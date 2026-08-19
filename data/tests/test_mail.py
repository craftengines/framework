"""Tests for Mail & Notification Subsystem in Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest
from craft.facades import Mail
from craft.mail.contracts import EmailMessage
from craft.mail.drivers.log import ArrayMailDriver, LogMailDriver
from craft.mail.mailable import Mailable


class UserWelcomeMailable(Mailable):
    subject = "Welcome to our Platform!"

    def __init__(self, username: str):
        super().__init__()
        self.username = username

    def build(self):
        return self.html(f"<h1>Hello, {self.username}!</h1>").text(f"Hello, {self.username}!")


class TestMail:
    def test_array_mail_driver(self):
        driver = ArrayMailDriver()
        msg = EmailMessage(to=["user@example.com"], subject="Test", body_text="Hello")
        assert driver.send(msg) is True
        assert len(driver.messages) == 1
        assert driver.messages[0].to == ["user@example.com"]

    def test_mailable_building(self):
        mailable = UserWelcomeMailable("Antonio")
        msg = mailable.to("antonio@example.com").to_email_message()
        assert msg.subject == "Welcome to our Platform!"
        assert msg.to == ["antonio@example.com"]
        assert "Antonio" in msg.body_text
        assert "<h1>Hello, Antonio!</h1>" in msg.body_html

    def test_fluent_mail_to_send(self):
        array_driver = ArrayMailDriver()
        Mail.set_mailer("array", array_driver)
        Mail.set_default_mailer("array")

        # 1. Send via fluent chain
        Mail.to("client@example.com").send(UserWelcomeMailable("Client"))
        msg = array_driver.messages[-1]
        assert msg.to == ["client@example.com"]
        assert "Client" in msg.body_text

    def test_mail_raw(self):
        array_driver = ArrayMailDriver()
        Mail.set_mailer("array", array_driver)
        Mail.set_default_mailer("array")

        Mail.raw("Your verification code is 123456", to="user@domain.com", subject="Verify Account")
        assert len(array_driver.messages) > 0
        last = array_driver.messages[-1]
        assert last.to == ["user@domain.com"]
        assert "123456" in last.body_text
