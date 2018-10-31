FROM ubuntu:18.04
MAINTAINER asi@dbca.wa.gov.au

WORKDIR /app
COPY gunicorn.ini manage.py requirements.txt ./
COPY fex.id /root/.fex/id
COPY pbs ./pbs
COPY pbs_project ./pbs_project
COPY smart_selects ./smart_selects
COPY swingers ./swingers
COPY templates ./templates
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
  && apt-get install -yq git mercurial gcc gdal-bin libsasl2-dev \
  python python-setuptools python-dev python-pip \
  fex-utils imagemagick poppler-utils \
  libldap2-dev libssl-dev wget build-essential \
  texlive texlive-latex-recommended texlive-fonts-extra lmodern latexmk \
  && pip install --no-cache-dir -r requirements.txt \
  # Update the bug in django/contrib/gis/geos/libgeos.py
  # Reference: https://stackoverflow.com/questions/18643998/geodjango-geosexception-error
  && sed -i -e "s/ver = geos_version().decode()/ver = geos_version().decode().split(' ')[0]/" /usr/local/lib/python2.7/dist-packages/django/contrib/gis/geos/libgeos.py \
  && python manage.py collectstatic --noinput \
  && rm -rf /var/lib/{apt,dpkg,cache,log}/ /tmp/* /var/tmp/*

HEALTHCHECK --interval=1m --timeout=5s --start-period=10s --retries=3 CMD ["wget", "-q", "-O", "-", "http://localhost:8080/"]
EXPOSE 8080
CMD ["gunicorn", "pbs_project.wsgi", "--config", "gunicorn.ini"]
