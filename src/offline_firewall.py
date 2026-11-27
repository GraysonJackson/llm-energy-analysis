"""Apply and verify temporary Windows outbound rules for the installed Ollama binaries."""

import ipaddress
import json
import os
import subprocess
from urllib.parse import urlsplit
from uuid import uuid4


PREFIX = 'llm-energy-ollama-check-'
REMOTE_RANGES = ('0.0.0.1-126.255.255.255', '128.0.0.0-255.255.255.255',
                 '::2-ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff')

DISCOVER = r'''
$port = [int]$env:LLM_OFFLINE_PORT
$listeners = @(Get-NetTCPConnection -LocalPort $port -State Listen)
if ($listeners.Count -ne 1 -or $listeners[0].LocalAddress -notin @('127.0.0.1', '::1')) {
    throw 'The Ollama listener must be bound to a single loopback address.'
}
$server = Get-Process -Id $listeners[0].OwningProcess
$root = Split-Path -Parent $server.Path
if ((Split-Path -Leaf $server.Path) -ne 'ollama.exe' -or (Split-Path -Leaf $root) -ne 'Ollama') {
    throw 'The loopback listener is outside the standard Ollama installation.'
}
$programs = @(Get-ChildItem -LiteralPath $root -Recurse -File -Filter '*.exe' |
    Where-Object Name -NotLike 'unins*.exe' | Select-Object -ExpandProperty FullName)
$profile = @(Get-NetFirewallProfile -PolicyStore ActiveStore)
$principals = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
@{
    administrator = $principals.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    server_pid = $server.Id
    programs = $programs
    profiles_enabled = ($profile.Count -eq 3 -and @($profile | Where-Object { "$($_.Enabled)" -ne 'True' }).Count -eq 0)
} | ConvertTo-Json -Compress
'''

INSTALL = r'''
$programs = @(ConvertFrom-Json $env:LLM_OFFLINE_PROGRAMS)
$ranges = $env:LLM_OFFLINE_RANGES.Split(',')
$group = $env:LLM_OFFLINE_GROUP
for ($i = 0; $i -lt $programs.Count; $i++) {
    New-NetFirewallRule -PolicyStore PersistentStore -Name "$group-$i" -DisplayName "$group-$i" -Group $group `
        -Program $programs[$i] -Direction Outbound -Action Block -Profile Any -Enabled True -RemoteAddress $ranges |
        Out-Null
}
'''

ACTIVE = r'''
$group = $env:LLM_OFFLINE_GROUP
$names = @(ConvertFrom-Json $env:LLM_OFFLINE_PROGRAMS)
$profile = @(Get-NetFirewallProfile -PolicyStore ActiveStore)
$rules = @(Get-NetFirewallRule -PolicyStore ActiveStore -Group $group -ErrorAction SilentlyContinue)
$record = @(foreach ($rule in $rules) {
    @{
        program = [string]($rule | Get-NetFirewallApplicationFilter).Program
        addresses = @($rule | Get-NetFirewallAddressFilter | Select-Object -ExpandProperty RemoteAddress)
        blocking = ("$($rule.Action)" -eq 'Block' -and "$($rule.Direction)" -eq 'Outbound' -and
                    "$($rule.Enabled)" -eq 'True' -and "$($rule.Profile)" -eq 'Any' -and
                    "$($rule.PrimaryStatus)" -eq 'OK')
    }
})
$pids = @(Get-Process | Where-Object { $_.Path -and $_.Path -in $names } | Select-Object -ExpandProperty Id)
$outside = @(Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue | Where-Object {
    $_.OwningProcess -in $pids -and $_.RemoteAddress -ne '::1' -and
        $_.RemoteAddress -notmatch '^(::ffff:)?127\.'
})
$listeners = @(Get-NetTCPConnection -LocalPort ([int]$env:LLM_OFFLINE_PORT) -State Listen -ErrorAction SilentlyContinue)
@{
    profiles_enabled = ($profile.Count -eq 3 -and @($profile | Where-Object { "$($_.Enabled)" -ne 'True' }).Count -eq 0)
    same_listener = ($listeners.Count -eq 1 -and $listeners[0].OwningProcess -eq [int]$env:LLM_OFFLINE_PID -and
                     $listeners[0].LocalAddress -in @('127.0.0.1', '::1'))
    rules = $record
    established_non_loopback_tcp = $outside.Count
} | ConvertTo-Json -Depth 5 -Compress
'''

REMOVE = r'''
$group = $env:LLM_OFFLINE_GROUP
Get-NetFirewallRule -PolicyStore PersistentStore -Group $group -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule
if (Get-NetFirewallRule -PolicyStore PersistentStore -Group $group -ErrorAction SilentlyContinue) {
    throw 'Temporary Ollama firewall rules are still present.'
}
'''


def powershell(script, variables):
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                             "$ErrorActionPreference = 'Stop'\n[Console]::OutputEncoding = "
                             '[System.Text.UTF8Encoding]::new($false)\n' + script],
                            env={**os.environ, **variables}, capture_output=True, encoding='utf-8',
                            errors='replace', timeout=45, check=False)
    if result.returncode:
        detail = result.stderr.strip().splitlines()
        raise RuntimeError(detail[0] if detail else 'Windows Firewall command failed')
    return json.loads(result.stdout) if result.stdout.strip() else None


def address_coverage(entries):
    ranges = []
    for entry in entries:
        first, delimiter, last = entry.partition('-')
        if delimiter:
            low, high = ipaddress.ip_address(first), ipaddress.ip_address(last)
        else:
            net = ipaddress.ip_network(first, strict=False)
            low, high = net.network_address, net.broadcast_address
        ranges.extend(ipaddress.summarize_address_range(low, high))
    return tuple(str(network) for version in (4, 6)
                 for network in ipaddress.collapse_addresses(net for net in ranges if net.version == version))


class OllamaFirewall:
    def __init__(self, host):
        address = urlsplit(host)
        if address.scheme != 'http' or address.hostname not in ('localhost', '127.0.0.1', '::1'):
            raise ValueError('The privacy test requires an HTTP loopback Ollama endpoint')
        self.group = PREFIX + uuid4().hex
        self.variables = {'LLM_OFFLINE_GROUP': self.group, 'LLM_OFFLINE_PORT': str(address.port or 80),
                          'LLM_OFFLINE_RANGES': ','.join(REMOTE_RANGES)}
        self.programs = []
        self.install_started = False

    def install(self):
        found = powershell(DISCOVER, self.variables)
        if not found['administrator']:
            raise RuntimeError('Open PowerShell as Administrator and run this check again')
        if not found['profiles_enabled'] or not found['programs']:
            raise RuntimeError('Windows Firewall must be enabled in all profiles for this check')
        self.programs = found['programs']
        self.variables.update(LLM_OFFLINE_PROGRAMS=json.dumps(self.programs), LLM_OFFLINE_PID=str(found['server_pid']))
        self.install_started = True
        powershell(INSTALL, self.variables)

    def state(self):
        observed = powershell(ACTIVE, self.variables)
        expected = address_coverage(REMOTE_RANGES)
        programs = {path.casefold() for path in self.programs}
        rules = observed['rules']
        observed['verified'] = (observed['profiles_enabled'] and observed['same_listener']
                                and observed['established_non_loopback_tcp'] == 0
                                and len(rules) == len(programs)
                                and {rule['program'].casefold() for rule in rules} == programs
                                and all(rule['blocking'] and address_coverage(rule['addresses']) == expected for rule in rules))
        return observed

    def remove(self):
        if self.install_started:
            powershell(REMOVE, self.variables)
