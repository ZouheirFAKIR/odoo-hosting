FROM odoo:18.0
USER root
COPY ./addons /mnt/extra-addons
COPY ./odoo.conf /etc/odoo/odoo.conf
RUN chown -R odoo:odoo /mnt/extra-addons /etc/odoo/odoo.conf
USER odoo
