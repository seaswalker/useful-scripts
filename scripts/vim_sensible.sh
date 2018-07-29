#!/bin/bash

# pathogen plugin manager
echo 'Now begin to install plugin manager pathogen...'
mkdir -p ~/.vim/autoload ~/.vim/bundle && \
curl -LSso ~/.vim/autoload/pathogen.vim https://tpo.pe/pathogen.vim
echo 'Pathogen done.'

echo 'Enable pathogen...'
echo -e '\n" enable pathogen\nexecute pathogen#infect()' >> ~/.vimrc
echo 'Enable pathogen done.'

# vim-sensible plugin
echo 'Install vim-sensible...'
cd ~/.vim/bundle
git clone git://github.com/tpope/vim-sensible.git
echo 'Vim-sensible done. Have fun!'
