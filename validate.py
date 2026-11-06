#!/usr/bin/env python3
"""Validate profile references, fetch remote lists, and replay domain routing.

Uses only the Python standard library and curl. Does not load node credentials.
This is a static routing check, not a substitute for a real Siri request.
"""
import argparse
import concurrent.futures
import fnmatch
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import subprocess
import tempfile

def parse(path):
    sections, section = {}, ''
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('['):
            section = line
            sections[section] = []
        else:
            sections[section].append(line)
    return sections

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', nargs='?', type=Path, default=Path(__file__).with_name('personal-apple-ai.conf'))
    parser.add_argument('--cache', type=Path, default=Path(tempfile.gettempdir()) / 'shadowrocket-public-rules-cache')
    args = parser.parse_args()
    data = parse(args.config)
    text = args.config.read_text()
    forbidden = ['ca-passphrase', 'ca-p12', 'vless://', 'ss://', 'trojan://', '/subscription/']
    assert not any(x in text.lower() for x in forbidden), 'Credential material detected'
    assert '[MITM]' not in data and '[Script]' not in data and '[Proxy]' not in data
    assert not re.search(r'(?mi)^update-url\s*=', text), 'Upstream replacement URL present'
    groups = {l.split(' = ',1)[0]:l.split(' = ',1)[1] for l in data['[Proxy Group]']}
    policies = set(groups) | {'PROXY','DIRECT','REJECT'}
    for name, definition in groups.items():
        if definition.startswith('select,'):
            for item in definition.split(',')[1:]:
                if '=' not in item:
                    assert item in policies, f'Unknown group member: {name} -> {item}'
    rules = [l.split(',') for l in data['[Rule]']]
    for parts in rules:
        policy = parts[1] if parts[0]=='FINAL' else parts[2]
        assert policy in policies, f'Unknown policy: {policy}'
    assert rules[-1]==['FINAL','PROXY']
    urls = list(dict.fromkeys(p[1] for p in rules if p[0] in ('RULE-SET','DOMAIN-SET')))
    args.cache.mkdir(parents=True, exist_ok=True)

    def fetch(url):
        assert url.startswith('https://raw.githubusercontent.com/'), 'Unexpected ruleset host'
        result = subprocess.run(['curl','--fail','--silent','--show-error','--location','--max-time','40','--retry','1',url], capture_output=True)
        if result.returncode:
            raise RuntimeError(f'Ruleset download failed: {url}')
        content = result.stdout.decode('utf-8-sig')
        (args.cache / (hashlib.sha256(url.encode()).hexdigest()+'.list')).write_text(content)
        return url, [l.strip() for l in content.splitlines() if l.strip() and not l.lstrip().startswith(('#',';','//'))]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        remote = dict(executor.map(fetch, urls))
    for parts in rules:
        if parts[0]=='DOMAIN-SET':
            for line in remote[parts[1]]:
                assert re.fullmatch(r'\.?[\w.*-]+(?:\.[\w*-]+)*',line), f'Invalid domain-set entry in {parts[1]}'
        elif parts[0]=='RULE-SET':
            allowed = {'DOMAIN','DOMAIN-SUFFIX','DOMAIN-KEYWORD','DOMAIN-WILDCARD','IP-CIDR','IP-CIDR6','IP-ASN','USER-AGENT','URL-REGEX'}
            for line in remote[parts[1]]:
                fields=line.split(',')
                assert fields[0] in allowed, f'Unexpected remote rule type: {fields[0]}'
                assert len(fields)==2 or (len(fields)==3 and fields[2]=='no-resolve'), 'Remote policy injection'

    def matches(fields, domain):
        kind,value=fields[:2]
        if kind=='DOMAIN': return domain==value
        if kind=='DOMAIN-SUFFIX': return domain==value or domain.endswith('.'+value)
        if kind=='DOMAIN-KEYWORD': return value in domain
        if kind=='DOMAIN-WILDCARD': return fnmatch.fnmatchcase(domain,value)
        return False
    def route(domain):
        for fields in rules:
            kind=fields[0]
            if kind=='FINAL': return fields[1]
            if kind=='DOMAIN-SET':
                for entry in remote[fields[1]]:
                    # Leading dot includes the apex and subdomains in Shadowrocket.
                    if (entry.startswith('.') and (domain==entry[1:] or domain.endswith(entry))) or domain==entry:
                        return fields[2]
            elif kind=='RULE-SET':
                if any(matches(l.split(','),domain) for l in remote[fields[1]]): return fields[2]
            elif matches(fields,domain): return fields[2]
        raise AssertionError('Missing final')
    cases={
        'guzzoni.apple.com':'SiriAI','api.smoot.apple.com':'SiriAI',
        'apple-relay.apple.com':'SiriAI','apple-relay.cloudflare.com':'SiriAI',
        'apple-relay.fastly-edge.com':'SiriAI','cp4.cloudflare.com':'SiriAI',
        'gspe1-ssl.ls.apple.com':'SiriAI','chatgpt.com':'AI','api.openai.com':'AI',
        'claude.ai':'AI','gemini.google.com':'AI','copilot.microsoft.com':'AI',
        'githubcopilot.com':'AI','github.com':'PROXY','raw.githubusercontent.com':'PROXY',
        'gitee.com':'DIRECT','registry.npmmirror.com':'DIRECT','mirrors.aliyun.com':'DIRECT',
        'mirrors.cloud.tencent.com':'DIRECT','www.apple.com':'苹果服务',
        'api.icloud.com':'苹果服务','init.push.apple.com':'苹果服务','apps.mzstatic.com':'苹果服务',
        'www.youtube.com':'YouTube','www.netflix.com':'Netflix','www.bilibili.com':'哔哩哔哩',
        'www.baidu.com':'DIRECT','dl.steam.clngaa.com':'DIRECT',
        'printer.local':'DIRECT',
    }
    results=[]
    for domain,expected in cases.items():
        actual=route(domain)
        assert actual==expected, f'{domain}: expected {expected}, got {actual}'
        results.append({'domain':domain,'policy':actual})
    print(json.dumps({'result':'PASS','rules':len(rules),'groups':len(groups),
                      'remote_rulesets_fetched':len(urls),'domain_checks':len(results),
                      'checks':results}, ensure_ascii=False, indent=2))

if __name__=='__main__':
    main()
