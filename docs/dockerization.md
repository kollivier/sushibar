

PHASE 1: Need to setup SSL

  - nginx
  - nginx-gen
     using template: https://github.com/jwilder/nginx-proxy/blob/master/nginx.tmpl
  - letsencrypt-nginx-proxy-companion



PHASE 2: dockerize sushibar code

2.1 django-wsgi app [DONE]
2.2 django-wsgi + django-asgi + asgi-worker + redis (blank app) [DONE]
2.3 move over code from waiter app by app [DONE]
2.4 simplify user model
3.5 custom login form
3.6 custom login view class (inherit from LoginView)
3.7 content curation server authentication backend



PHASE 3: add optino to run sushibar in local VM using docker dev (e.g for Windows)


PHASE 4: (optional) create staging env, comletely separate from prod



