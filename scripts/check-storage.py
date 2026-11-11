#!/usr/bin/env python3
"""Verify cold-boot persistence and guest power control on an isolated data disk."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent.parent


def run_boot(directory,disk,cases,shutdown):
    directory.mkdir()
    scenario=directory/'cases.json'
    scenario.write_text(json.dumps(cases,indent=2)+'\n')
    command=[sys.executable,str(ROOT/'scripts/boot-qemu.py'),'--seconds','120',
             '--root-image',str(ROOT/'build/rootfs/root.hfs'),'--disk-image',str(disk),
             '--check-console','--console-case-file',str(scenario),'--expect-shutdown',shutdown,
             '--output',str(directory)]
    with (directory/'output.log').open('w') as log:
        subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT)
    data=json.loads((directory/'diagnostics.json').read_text())
    output=(directory/'serial.log').read_text(errors='replace')
    if 'persistent /data mounted' not in output or 'flushing fs disk buffer returned' in output:
        raise ValueError('persistent volume or cache flush verification failed: '+str(directory))
    if directory.name!='write-poweroff' and 'replay_journal' in output:
        raise ValueError('previous shutdown left a dirty journal: '+str(directory))
    if 'hfs: unmount initiated on commonplace-data' not in output:
        raise ValueError('guest did not unmount its persistent filesystem')
    return data


def case(name,send,expected): return {'name':name,'send':send+'\n','expect':expected}


def main():
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    directory=ROOT/'build/storage-checks'/stamp
    directory.mkdir(parents=True)
    disk=directory/'data.hfs'
    subprocess.run([sys.executable,str(ROOT/'scripts/create-disk.py'),'--path',str(disk)],check=True)
    token=hashlib.sha256(stamp.encode()).hexdigest()[:24]
    first=[case('utf8 terminal','echo привет',r'\nпривет\n'),
           case('utf8 filename','echo данные > /data/имя',r'\Aecho данные > /data/имя\n\Z'),
           case('write file',f'echo {token} > /data/probe',rf'\Aecho {token} > /data/probe\n\Z'),
           case('write beyond one buffer','seq 1 10000 > /data/large',r'\Aseq 1 10000 > /data/large\n\Z'),
           case('copy executable','cp /bin/echo /data/saved-program',r'\Acp /bin/echo /data/saved-program\n\Z'),
           case('protect identical source','cp /data/probe /data/./probe',r'identical|same file'),
           case('source remains intact','cat /data/probe',rf'\n{token}\n'),
           case('edit persistent text',r"touch /data/note; printf 'a\nfirst line\nsecond line\n.\n1d\nw\nq\n' | ed -s /data/note",r'printf'),
           case('verify edited file','cat /data/note',r'\Acat /data/note\nsecond line\n\Z'),
           case('discard unsaved edits',r"printf 'a\nunsaved\n.\nQ\n' | ed -s /data/note",r'printf'),
           case('original not overwritten','cat /data/note',r'\Acat /data/note\nsecond line\n\Z'),
           case('install startup script',"printf '%s\\n' 'echo startup-ok > /data/boot-marker' > /data/rc",r'printf')]
    reader=[case('read after power cycle','cat /data/probe',rf'\n{token}\n'),
            case('verify complete file','wc -l < /data/large',r'\n[ \t]*10000\n'),
            case('execute cold file','/data/saved-program persisted-executable',r'\npersisted-executable\n'),
            case('utf8 file persisted','cat /data/имя',r'\nданные\n'),
            case('edited file persisted','cat /data/note',r'\nsecond line\n'),
            case('startup script executed','cat /data/boot-marker',r'\nstartup-ok\n')]
    phases=[]
    phases.append(run_boot(directory/'write-poweroff',disk,first,'poweroff'))
    phases.append(run_boot(directory/'read-reboot',disk,reader,'reboot'))
    broken=reader+[case('install bounded failure','echo \'sleep 60\' > /data/rc',r'\Aecho \'sleep 60\' > /data/rc\n\Z')]
    phases.append(run_boot(directory/'read-poweroff',disk,broken,'poweroff'))
    recovered=[case('remove faulty startup script','rm /data/rc',r'\Arm /data/rc\n\Z'),
               case('recovered console','echo startup-timeout-recovered',r'\nstartup-timeout-recovered\n')]
    phases.append(run_boot(directory/'startup-timeout',disk,recovered,'poweroff'))
    if 'startup script timed out' not in (directory/'startup-timeout/serial.log').read_text():
        raise ValueError('startup timeout path was not exercised')
    artifacts={tuple(sorted(phase['sha256'].items())) for phase in phases}
    if len(artifacts)!=1: raise ValueError('boot artifacts changed between persistence checks')
    extracted=directory/'probe'
    subprocess.run([str(ROOT/'toolchain/bin/hfsplus'),str(disk),'extract','/probe',str(extracted)],check=True)
    if extracted.read_bytes()!=(token+'\n').encode(): raise ValueError('host filesystem verification failed')
    summary={'phases':len(phases),'token':token,'disk':str(disk),'passed':True,
             'boot_artifacts':phases[0]['sha256'],'shutdown':[phase['shutdown'] for phase in phases]}
    (directory/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('persistent files survived poweroff and reboot; evidence: '+str(directory))


if __name__=='__main__': main()
