# Prescribed Burn System

The Prescribed Burn System is used by officers within the Department of Parks & Wildlife (DPaW)
to generate and manage electronic Prescribed Fire Plans (ePFP).

Troubleshooting and support page on Confluence:
[PBS application support](https://confluence.dpaw.wa.gov.au/display/PBS/PBS+application+support)

# Installation

Create a new virtualenv and install required libraries using `pip`:

    pip install -r requirements.txt

# Environment variables

This project uses `django-confy` to set environment
variables (in a `.env` file). Required settings are as follows:

    DJANGO_SETTINGS_MODULE="pbs_project.settings"
    DEBUG=True
    DATABASE_URL="postgis://USER:PASSWORD@HOST:PORT/DATABASE_NAME"
    SECRET_KEY="ThisIsASecretKey"
    LDAP_SERVER_URI="ldap://URL"
    LDAP_ACCESS_DN="ldap-access-dn"
    LDAP_ACCESS_PASSWORD="password"
    LDAP_SEARCH_SCOPE="DC=searchscope"
    EMAIL_HOST="email.host"
