#!/bin/bash
exec odoo --db_host="$HOST" --db_port=5432 --db_user="$USER" --db_password="$PASSWORD" --db_sslmode=require -i base,approval_workflow --without-demo=all
