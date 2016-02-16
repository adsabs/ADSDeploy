#!/bin/bash -e

# this script will deploy [or update] the eb-deploy
# into the current working directory. you have to
# be prepared to supply your github credentials 
# and AWS secrets

if [ ! -e eb-deploy ]; then
	git clone git@github.com:adsabs/eb-deploy.git
	
else
	pushd eb-deploy
	git pull
	popd
fi


pushd eb-deploy
virtualenv python
source python/bin/activate
pip install -r requirements.txt


# test we have access
pushd bumblebee/bumblebee
./st > /dev/null

if [ ! $? -eq 0 ]; then
	echo -n "The AWS needs to be configured. I'll execure 'eb init'. Ready? [y]" answer
	if [ "${answer:-y}" == "y" ]; then
		eb init
	else
		echo "The eb scripts will not work unless you set AWS credentials."
	fi
fi