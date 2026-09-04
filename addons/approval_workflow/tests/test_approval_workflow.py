# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestApprovalWorkflow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.Category = cls.env["approval.category"]
        cls.Workflow = cls.env["approval.workflow"]
        cls.Stage = cls.env["approval.stage"]

        cls.category = cls.Category.create({
            "name": "Workflow Test Category",
        })

    def test_01_create_sequential_workflow(self):

        workflow = self.Workflow.create({
            "name": "Sequential Workflow",
            "category_id": self.category.id,
            "mode": "sequential",
        })

        self.assertTrue(workflow)
        self.assertEqual(workflow.mode, "sequential")

    def test_02_create_parallel_workflow(self):

        workflow = self.Workflow.create({
            "name": "Parallel Workflow",
            "category_id": self.category.id,
            "mode": "parallel",
        })

        self.assertTrue(workflow)
        self.assertEqual(workflow.mode, "parallel")

    def test_03_stage_ordering(self):

        workflow = self.Workflow.create({
            "name": "Ordering Workflow",
            "category_id": self.category.id,
            "mode": "sequential",
        })

        stage_20 = self.Stage.create({
            "name": "Stage 20",
            "workflow_id": workflow.id,
            "sequence": 20,
            "approval_type": "any",
        })

        stage_10 = self.Stage.create({
            "name": "Stage 10",
            "workflow_id": workflow.id,
            "sequence": 10,
            "approval_type": "any",
        })

        stages = workflow.stage_ids.sorted("sequence")

        self.assertEqual(stages[0], stage_10)
        self.assertEqual(stages[1], stage_20)

    def test_04_workflow_contains_stages(self):

        workflow = self.Workflow.create({
            "name": "Workflow With Stages",
            "category_id": self.category.id,
            "mode": "sequential",
        })

        self.Stage.create({
            "name": "Stage A",
            "workflow_id": workflow.id,
            "sequence": 10,
            "approval_type": "any",
        })

        self.Stage.create({
            "name": "Stage B",
            "workflow_id": workflow.id,
            "sequence": 20,
            "approval_type": "any",
        })

        self.assertEqual(len(workflow.stage_ids), 2)

    def test_05_stage_sequence_integrity(self):

        workflow = self.Workflow.create({
            "name": "Integrity Workflow",
            "category_id": self.category.id,
            "mode": "sequential",
        })

        sequences = [10, 20, 30]

        for seq in sequences:
            self.Stage.create({
                "name": f"Stage {seq}",
                "workflow_id": workflow.id,
                "sequence": seq,
                "approval_type": "any",
            })

        ordered = workflow.stage_ids.sorted("sequence")

        self.assertEqual(
            ordered.mapped("sequence"),
            [10, 20, 30]
        )

    def test_06_parallel_stages_allowed(self):

        workflow = self.Workflow.create({
            "name": "Parallel Validation Workflow",
            "category_id": self.category.id,
            "mode": "parallel",
        })

        self.Stage.create({
            "name": "HR",
            "workflow_id": workflow.id,
            "sequence": 10,
            "approval_type": "any",
        })

        self.Stage.create({
            "name": "Manager",
            "workflow_id": workflow.id,
            "sequence": 10,
            "approval_type": "any",
        })

        self.assertEqual(
            len(workflow.stage_ids),
            2
        )

    def test_07_category_link(self):

        workflow = self.Workflow.create({
            "name": "Category Link Workflow",
            "category_id": self.category.id,
            "mode": "sequential",
        })

        self.assertEqual(
            workflow.category_id,
            self.category
        )

    def test_08_archive_workflow(self):

        workflow = self.Workflow.create({
            "name": "Archive Workflow",
            "category_id": self.category.id,
            "mode": "sequential",
            "active": True,
        })

        workflow.active = False

        self.assertFalse(workflow.active)