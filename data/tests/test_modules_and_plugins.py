"""Test suite verifying Craft Engine Business Modules and Capability Plugins architecture."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest
from app.plugins.brazil_validator.engine import DocumentValidatorEngine
from app.plugins.brazil_validator.plugin import PLUGIN as BRAZIL_VALIDATOR_PLUGIN, register as register_brazil_validator
from app.plugins.qrcode_generator.engine import QRCodeGeneratorEngine
from app.plugins.qrcode_generator.schemas import QRCodeOptions
from app.plugins.qrcode_generator.plugin import PLUGIN as QRCODE_PLUGIN, register as register_qrcode
from app.plugins.seo_optimizer.engine import SeoOptimizerEngine
from app.plugins.seo_optimizer.plugin import PLUGIN as SEO_PLUGIN, register as register_seo

from app.modules.cms.module import MODULE as CMS_MODULE, register as register_cms, boot as boot_cms
from app.modules.cms.services.cms_service import CmsService
from app.modules.cms.schemas.cms_schema import CreatePostData
from app.modules.cms.controllers.post_controller import PostController

from app.modules.billing.module import MODULE as BILLING_MODULE, register as register_billing, boot as boot_billing
from app.modules.billing.services.billing_service import BillingService
from app.modules.billing.schemas.billing_schema import CreateBankSlipData, CreateInvoiceData
from app.modules.billing.controllers.bank_slip_controller import BankSlipController

from engine.plugins.manager import PluginManager
from engine.container.application import Container


class DummyRequest:
    def __init__(self, inputs=None, expects_json=True):
        self._inputs = inputs or {}
        self._expects_json = expects_json

    def input(self, key, default=None):
        return self._inputs.get(key, default)

    def expects_json(self):
        return self._expects_json


class TestCapabilityPlugins:
    """Verify stateless capability plugins and engines."""

    def test_brazil_validator_cpf_valid(self):
        res = DocumentValidatorEngine.validate_cpf("529.982.247-25")
        assert res.is_valid is True
        assert res.document_type == "CPF"
        assert res.formatted_document == "529.982.247-25"

    def test_brazil_validator_cpf_invalid(self):
        res = DocumentValidatorEngine.validate_cpf("111.444.777-00")
        assert res.is_valid is False
        assert "invalid" in res.error_message.lower()

    def test_brazil_validator_cnpj_valid(self):
        res = DocumentValidatorEngine.validate_cnpj("11.222.333/0001-81")
        assert res.is_valid is True
        assert res.document_type == "CNPJ"

    def test_brazil_validator_cnpj_invalid(self):
        res = DocumentValidatorEngine.validate_cnpj("11.222.333/0001-00")
        assert res.is_valid is False

    def test_qrcode_generator_output(self):
        opts = QRCodeOptions(box_size=5, fill_color="#111111")
        res = QRCodeGeneratorEngine.generate_svg("https://craft.engine", opts)
        assert "<svg" in res.svg_output
        assert 'fill="#111111"' in res.svg_output
        assert res.metadata["dimension"] > 0

    def test_seo_optimizer_slugification_and_analysis(self):
        slug = SeoOptimizerEngine.slugify("Craft Engine: Modern Python Framework!")
        assert slug == "craft-engine-modern-python-framework"

        analysis = SeoOptimizerEngine.analyze_content(
            "Short Title",
            "This is a sample post body used for testing SEO metrics computation."
        )
        assert analysis.slug == "short-title"
        assert analysis.word_count > 0
        assert len(analysis.suggestions) > 0

    def test_plugin_manifest_descriptors(self):
        assert BRAZIL_VALIDATOR_PLUGIN["slug"] == "brazil_validator"
        assert QRCODE_PLUGIN["slug"] == "qrcode_generator"
        assert SEO_PLUGIN["slug"] == "seo_optimizer"


class TestBusinessModules:
    """Verify business modules lifecycle, domain services, repositories, and thin controllers."""

    def test_cms_module_bootstrap_and_service(self, migrated_database):
        from app.Models.User import User
        user = User.create({"name": "CMS User", "email": "cms_user@test.com", "password": "password"})

        assert CMS_MODULE["slug"] == "cms"

        container = Container()
        register_cms(container)

        service = container.make("module.cms.service")
        assert isinstance(service, CmsService)

        post_res = service.create_post(CreatePostData(
            title="Modular Craft Engine",
            body="Encapsulating domain workflows into business modules.",
            user_id=user.get_attribute("id"),
        ))

        assert post_res["post"].get_attribute("title") == "Modular Craft Engine"
        assert "seo_analysis" in post_res

    def test_cms_thin_post_controller(self, migrated_database):
        from app.Models.User import User
        user = User.create({"name": "Author", "email": "author@test.com", "password": "password"})

        service = CmsService()
        controller = PostController(service=service)

        req = DummyRequest(inputs={
            "title": "Controller Post",
            "body": "Thin controller transport layer test.",
            "user_id": user.get_attribute("id"),
        }, expects_json=True)

        res = controller.store(req)
        assert res.status_code == 201

    def test_billing_module_bank_slip_issuance(self):
        assert BILLING_MODULE["slug"] == "billing"

        service = BillingService()
        data = CreateBankSlipData(
            customer_name="Acme Corp",
            customer_document="11.222.333/0001-81",
            amount=1500.50,
            due_date="2026-12-31",
        )

        slip = service.issue_bank_slip(data)
        assert slip["customer_name"] == "Acme Corp"
        assert slip["customer_document"] == "11.222.333/0001-81"
        assert "34191." in slip["barcode"]

    def test_billing_invalid_document_raises_error(self):
        service = BillingService()
        data = CreateBankSlipData(
            customer_name="Invalid Customer",
            customer_document="000.000.000-00",
            amount=100.0,
            due_date="2026-12-31",
        )

        with pytest.raises(ValueError) as exc_info:
            service.issue_bank_slip(data)
        assert "invalid customer document" in str(exc_info.value).lower()

    def test_billing_thin_bank_slip_controller(self):
        service = BillingService()
        controller = BankSlipController(service=service)

        req = DummyRequest(inputs={
            "customer_name": "Valid Client",
            "customer_document": "529.982.247-25",
            "amount": 250.00,
            "due_date": "2026-12-31",
        }, expects_json=True)

        res = controller.store(req)
        assert res.status_code == 201
