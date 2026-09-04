# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestApprovalRules(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.Category = cls.env["approval.category"]
        cls.Workflow = cls.env["approval.workflow"]
        cls.Stage = cls.env["approval.stage"]
        cls.Rule = cls.env["approval.rule"]

        cls.category = cls.Category.create({
            "name": "Rules Test Category",
        })

        cls.workflow = cls.Workflow.create({
            "name": "Rules Test Workflow",
            "category_id": cls.category.id,
            "mode": "sequential",
        })

        cls.Stage.create({
            "name": "Manager Validation",
            "workflow_id": cls.workflow.id,
            "sequence": 10,
            "approval_type": "any",
        })

    def test_01_create_rule(self):
        rule = self.Rule.create({
            "name": "Test Amount Rule",
            "workflow_id": self.workflow.id,
            "active": True,
        })

        self.assertTrue(rule)
        self.assertEqual(rule.workflow_id, self.workflow)
        self.assertTrue(rule.active)

    def test_02_rule_is_linked_to_workflow(self):
        rule = self.Rule.create({
            "name": "Workflow Rule",
            "workflow_id": self.workflow.id,
            "active": True,
        })

        self.assertIn(rule, self.workflow.rule_ids)

    def test_03_archive_rule(self):
        rule = self.Rule.create({
            "name": "Archive Test Rule",
            "workflow_id": self.workflow.id,
            "active": True,
        })

        rule.active = False

        self.assertFalse(rule.active)

    def test_04_multiple_rules(self):
        rule_1 = self.Rule.create({
            "name": "Rule 1",
            "workflow_id": self.workflow.id,
            "active": True,
        })

        rule_2 = self.Rule.create({
            "name": "Rule 2",
            "workflow_id": self.workflow.id,
            "active": True,
        })

        self.assertIn(rule_1, self.workflow.rule_ids)
        self.assertIn(rule_2, self.workflow.rule_ids)

    def test_05_find_workflow_method_exists(self):
        self.assertTrue(
            hasattr(self.Rule, "find_workflow"),
            "La méthode find_workflow doit exister.",
        )

    def test_06_rule_workflow_category(self):
        rule = self.Rule.create({
            "name": "Category Workflow Rule",
            "workflow_id": self.workflow.id,
            "active": True,
        })

        self.assertEqual(
            rule.workflow_id.category_id,
            self.category,
        )

    def test_07_only_active_rules_are_active(self):
        active_rule = self.Rule.create({
            "name": "Active Rule",
            "workflow_id": self.workflow.id,
            "active": True,
        })

        inactive_rule = self.Rule.create({
            "name": "Inactive Rule",
            "workflow_id": self.workflow.id,
            "active": False,
        })

        self.assertTrue(active_rule.active)
        self.assertFalse(inactive_rule.active)