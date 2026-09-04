FROM odoo:18.0
USER root
COPY ./addons /mnt/extra-addons
COPY ./odoo.conf /etc/odoo/odoo.conf
COPY ./start.sh /start.sh
RUN chown -R odoo:odoo /mnt/extra-addons /etc/odoo/odoo.conf && chmod +x /start.sh
USER odoo
CMD ["/start.sh"]