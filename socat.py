#!/usr/bin/python3

import argparse
import os
import re
import subprocess


def get_dict(d, key):
    if type(d) is not dict:
        raise Exception('not dict')
    dd = d.get(key)
    if dd is None:
        return ''
    return dd


def socat_port():
    output = subprocess.check_output("ps aux | grep socat", shell=True, universal_newlines=True)

    out = []
    for line in output.splitlines():
        match = re.compile(r'socat (\w+)-LISTEN:(\d+)').search(line)
        if not match:
            continue
        data = {
            'listen_protocol': match.group(1).upper(),
            'listen_port': match.group(2)
        }

        match = re.compile(r'(\w+):([^:]+):(\d+)$').search(line)
        if not match:
            continue
        data['remote_protocol'] = match.group(1).upper()
        data['remote_host'] = match.group(2)
        data['remote_port'] = match.group(3)

        match = re.compile(r'(\d+)').search(line)
        if not match:
            continue
        data['listen_pid'] = match.group(1)

        match = re.compile(r',range=([^,]+),').search(line)
        if match:
            data['listen_range'] = match.group(1)
        match = re.compile(r',bind=([^,]+),').search(line)
        if match:
            data['listen_bind'] = match.group(1)
        out.append(data)

    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--range', help='监听网段范围，例如：192.168.1.0/24')
    parser.add_argument('-b', '--bind', help='绑定监听地址，例如：192.168.1.1')
    parser.add_argument('-p', '--protocol', default='all', help='[all | tcp | udp]')
    parser.add_argument('positional', nargs='*',
                        help='<add | del | list> <本地端口> <远程地址>，例如：add 8000 192.168.1.2:8080')

    args = parser.parse_args()

    try:
        operation = args.positional[0]
        if operation != 'list':
            if len(args.positional) != 3:
                raise Exception()

            port = int(args.positional[1])
            raddr = args.positional[2]

            if not 0 < port < 1 << 16:
                print('端口不正确')
                exit(1)
    except:
        parser.print_usage()
        exit(1)

    if operation == 'add':
        command = 'socat {protocol}-LISTEN:{port},{option}fork,reuseaddr {protocol}:{raddr} &'
        option = ''
        if args.range is not None:
            option += 'range=%s,' % args.range
        if args.bind is not None:
            option += 'bind=%s,' % args.bind

        commands = []
        if args.protocol == 'all':
            commands.append({'protocol': 'TCP',
                             'command': command.format(protocol='TCP', port=port, option=option, raddr=raddr)})
            commands.append({'protocol': 'UDP',
                             'command': command.format(protocol='UDP', port=port, option=option, raddr=raddr)})
        elif args.protocol == 'tcp':
            commands.append({'protocol': 'TCP',
                             'command': command.format(protocol='TCP', port=port, option=option, raddr=raddr)})
        elif args.protocol == 'udp':
            commands.append({'protocol': 'UDP',
                             'command': command.format(protocol='UDP', port=port, option=option, raddr=raddr)})
        list = socat_port()
        for c in commands:
            bk = False
            for data in list:
                if data.get('listen_port') == str(c.get('port')) and data.get('listen_protocol') == c.get(
                        'protocol').upper():
                    bk = True
                    break
            if bk:
                print('{protocol} {port} 已被占用'.format(protocol=c.get('protocol'), port=c.get('port')))
                continue
            os.system(c.get('command'))
    elif operation == 'del':
        list = socat_port()
        command = 'kill %s'
        commands = []
        for data in list:
            if args.protocol != 'all' and data.get('listen_protocol') != args.protocol:
                continue
            if str(port) != data.get('listen_port'):
                continue
            commands.append(command % data.get('listen_pid'))

        for c in commands:
            os.system(c)
    elif operation == 'list':
        layout = '{listen_protocol}\t{listen_port}\t{listen_bind}\t{listen_range}\t{remote}'
        # print(layout.format(listen_protocol=''))
        for data in socat_port():
            print(layout.format(
                listen_protocol=get_dict(data, 'listen_protocol'),
                listen_port=get_dict(data, 'listen_port'),
                listen_bind=get_dict(data, 'listen_bind'),
                listen_range=get_dict(data, 'listen_range'),
                remote='%s:%s:%s' % (
                    get_dict(data, 'remote_protocol'), get_dict(data, 'remote_host'), get_dict(data, 'remote_port')),
            ))
    else:
        print('参数不正确')
        parser.print_usage()
        exit(1)
