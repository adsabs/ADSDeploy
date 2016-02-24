#/bin/bash -ev

git config --global user.name "anon"
git config --global user.email "anon@anon.com"
cd /app

git fetch --tags
git pull

latest_tag=`git describe --tags $(git rev-list --tags --max-count=1)`

if [ -f latest-production ]; then
    latest=`cat latest-production`
    if [ "$latest" == "$latest_tag" ]; then
      exit 0
    fi
fi

echo `date` "Deploying $latest_tag" >> /var/log/automated-pulls

# checkout latest release tag
git checkout --force $latest_tag

#Provision libraries/database
pip install -r requirements.txt
pip install -r web-requirements.txt

alembic upgrade head

echo $latest_tag > latest-production

# copy the deployment targets and ourselves
cp manifests/production/app/gitpull.sh $0
cp manifests/production/app/run_pipeline /etc/service/pipeline/run
cp manifests/production/app/run_webapp /etc/service/webapp/run
cp manifests/production/app/run_ebdeploy /etc/service/ebdeploy/run

# restart all services
sv restart pipeline
sv restart ebdeploy
sv restart webapp
