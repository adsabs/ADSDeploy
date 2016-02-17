FROM phusion/baseimage:0.9.17


RUN apt-get update --fix-missing
RUN apt-get install -y python-pip ipython python-dev libpq-dev git python-virtualenv gunicorn zip
RUN pip install --upgrade pip

RUN mkdir -p /etc/service/app
ADD run /etc/service/app/run
RUN chmod +x /etc/service/app/run

# you must obtain this key and place it in
# the folder (it is intentionally missing)
ADD eb-deploy-key /root/.ssh/eb-deploy-key
ADD aws_config /root/.aws/config

ADD ssh_config /root/.ssh/config
ADD eb-deploy-key.pub /root/.ssh/eb-deploy-key.pub
RUN bash -c "chmod -R 0600 ~/.ssh/"

WORKDIR /app
RUN git clone https://github.com/adsabs/ADSDeploy /app
RUN git pull && git reset --hard HEAD

ADD eb-deploy-setup.sh ./
RUN chmod +x eb-deploy-setup.sh
RUN ./eb-deploy-setup.sh

ADD gitpull.cronjob /
ADD gitpull.sh /
RUN chmod +x /gitpull.sh
RUN crontab /gitpull.cronjob


RUN mkdir -p /etc/service/app
ADD run /etc/service/app/run
RUN chmod +x /etc/service/app/run

RUN mkdir -p /etc/service/webapp
ADD run_webapp /etc/service/webapp/run
RUN chmod +x /etc/service/webapp/run

RUN mkdir -p /etc/service/ebdeploy
ADD run_ebdeploy /etc/service/ebdeploy/run
RUN chmod +x /etc/service/ebdeploy/run

CMD ["/sbin/my_init"]