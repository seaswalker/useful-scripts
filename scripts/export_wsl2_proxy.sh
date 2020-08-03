#!/bin/bash

# 使用source命令执行此脚本！

# Trojan-qt5默认
port=58591
if [ $# -eq 1 ];
then
    port=$1
fi

host_ip=`cat /etc/resolv.conf | grep nameserver | awk '{print $2}'`
echo "Windows物理机IP: $host_ip"

echo "代理端口: $port"

export http_proxy="http://$host_ip:$port"

# 代理客户端没有https，否则会报proxyconnect tcp: EOF错误
export https_proxy="http://$host_ip:$port"

echo '设置完成'
