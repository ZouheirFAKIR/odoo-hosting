#!/bin/bash
echo "===== START.SH IS RUNNING ====="
exec odoo --db_host="$HOST" --db_port=5432 --db_user="$USER" --db_password="$PASSWORD" --db_sslmode=require -d neondb -i base,approval_workflow --without-demo=all
