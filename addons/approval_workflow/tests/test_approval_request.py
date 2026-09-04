# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestApprovalRequest(TransactionCase):
    """Tests fonctionnels du cycle de vie des demandes."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.User = cls.env["res.users"]
        cls.Category = cls.env["approval.category"]
        cls.Workflow = cls.env["approval.workflow"]
        cls.Stage = cls.env["approval.stage"]
        cls.Request = cls.env["approval.request"]

        cls.user = cls.env.ref("base.user_admin")

        cls.category = cls.Category.create({
            "name": "Test - Demande générale",
            "description": "Catégorie utilisée pour les tests.",
        })

        cls.workflow = cls.Workflow.create({
            "name": "Test - Workflow séquentiel",
            "category_id": cls.category.id,
            "mode": "sequential",
        })

        cls.stage = cls.Stage.create({
            "name": "Test - Validation Manager",
            "workflow_id": cls.workflow.id,
            "sequence": 10,
            "approval_type": "any",
            "approver_ids": [(6, 0, [cls.user.id])],
        })

    def _create_request(self):
        """Créer une demande de test."""
        return self.Request.create({
            "name": "TEST/APPROVAL/001",
            "requester_id": self.user.id,
            "category_id": self.category.id,
            "workflow_id": self.workflow.id,
            "description": "Demande créée automatiquement pour les tests.",
            "company_id": self.env.company.id,
        })

    def test_01_create_request(self):
        """Vérifier la création d'une demande."""
        request = self._create_request()

        self.assertTrue(request.exists())
        self.assertEqual(request.requester_id, self.user)
        self.assertEqual(request.category_id, self.category)
        self.assertEqual(request.workflow_id, self.workflow)
        self.assertEqual(request.company_id, self.env.company)

    def test_02_initial_state(self):
        """Une nouvelle demande doit être en brouillon."""
        request = self._create_request()

        self.assertEqual(
            request.state,
            "draft",
            "Une nouvelle demande doit être en état brouillon.",
        )

    def test_03_submit_request(self):
        """Vérifier la soumission d'une demande."""
        request = self._create_request()

        request.action_submit()

        self.assertNotEqual(
            request.state,
            "draft",
            "Après soumission, la demande ne doit plus être en brouillon.",
        )

    def test_04_approve_request(self):
        """Vérifier l'approbation par l'approbateur."""
        request = self._create_request()

        request.action_submit()

        self.env.user = self.user

        request.action_approve()

        self.assertIn(
            request.state,
            ("approved", "pending"),
            "Après une approbation valide, la demande doit être "
            "approuvée ou passer à l'étape suivante.",
        )

    def test_05_refuse_request(self):
        """Vérifier le refus d'une demande."""
        request = self._create_request()

        request.action_submit()

        request.action_refuse()

        self.assertEqual(
            request.state,
            "refused",
            "Une demande refusée doit passer à l'état refused.",
        )

    def test_06_cancel_request(self):
        """Vérifier l'annulation d'une demande."""
        request = self._create_request()

        request.action_cancel()

        self.assertEqual(
            request.state,
            "cancelled",
            "Une demande annulée doit passer à l'état cancelled.",
        )

    def test_07_cannot_approve_cancelled_request(self):
        """Une demande annulée ne doit plus pouvoir être approuvée."""
        request = self._create_request()

        request.action_cancel()

        with self.assertRaises(UserError):
            request.action_approve()

    def test_08_cannot_refuse_cancelled_request(self):
        """Une demande annulée ne doit plus pouvoir être refusée."""
        request = self._create_request()

        request.action_cancel()

        with self.assertRaises(UserError):
            request.action_refuse()

    def test_09_workflow_is_assigned(self):
        """Vérifier que le workflow est correctement associé."""
        request = self._create_request()

        self.assertTrue(request.workflow_id)
        self.assertEqual(
            request.workflow_id,
            self.workflow,
        )

    def test_10_workflow_contains_stage(self):
        """Vérifier que le workflow contient bien son étape."""
        self.assertIn(
            self.stage,
            self.workflow.stage_ids,
        )