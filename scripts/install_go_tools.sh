#!/bin/bash

echo "开始安装..."

go get -u github.com/ramya-rao-a/go-outline
go get -u github.com/acroca/go-symbols
go get -u golang.org/x/tools/cmd/guru
go get -u golang.org/x/tools/cmd/gorename
go get -u github.com/cweill/gotests/...
go get -u github.com/fatih/gomodifytags
go get -u github.com/josharian/impl
go get -u github.com/davidrjenni/reftools/cmd/fillstruct
go get -u github.com/haya14busa/goplay/cmd/goplay
go get -u github.com/godoctor/godoctor
go get -u github.com/derekparker/delve/cmd/dlv
go get -u github.com/stamblerre/gocode
go get -u github.com/rogpeppe/godef
go get -u github.com/sqs/goreturns
go get -u golang.org/x/lint/golint
go get -u golang.org/x/tools/cmd/goimports
go get -u github.com/go-delve/delve/cmd/dlv
go get -v github.com/uudashr/gopkgs/v2/cmd/gopkgs
go get -v golang.org/x/tools/gopls

echo "安装完成"
