#!/bin/sh

# 使用source命令执行此脚本！

# clashx
port=7890
if [ $# -eq 1 ];
then
    port=$1
fi

# sed used to remove the leading blank space and the trailing '^M' windows controll character
host_ip=`ipconfig.exe | grep 'IPv4 Address' | cut -d ':' -f 2 | sed 's/^.//;s/.$//'`

echo "Windows物理机IP: $host_ip"

echo "代理端口: $port"

export http_proxy="http://$host_ip:$port"

# 代理客户端没有https，否则会报proxyconnect tcp: EOF错误
export https_proxy="http://$host_ip:$port"

echo '设置完成'
