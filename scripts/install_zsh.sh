!#/bin/zsh

echo "Install zsh..."
sudo apt-get install zsh

echo "Install oh-my-zsh..."
sh -c "$(curl -fsSL https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"

echo "Set zsh as default sh..."
chsh -s `which zsh`

echo "ZSH_THEME=\"agnoster\"" >> ~/.zshrc

echo "done."