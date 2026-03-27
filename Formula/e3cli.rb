# Homebrew formula for e3cli
# Install: brew tap <your-github-user>/e3cli && brew install e3cli
# 或建立獨立 tap repo: homebrew-e3cli

class E3cli < Formula
  include Language::Python::Virtualenv

  desc "NYCU E3 Moodle automation CLI — sync courses, download materials, submit assignments"
  homepage "https://github.com/user/e3cli"
  url "https://github.com/user/e3cli/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA256"
  license "MIT"

  depends_on "python@3.12"

  resource "typer" do
    url "https://files.pythonhosted.org/packages/typer/typer-0.9.0.tar.gz"
    sha256 "REPLACE_WITH_ACTUAL_SHA256"
  end

  resource "requests" do
    url "https://files.pythonhosted.org/packages/requests/requests-2.31.0.tar.gz"
    sha256 "REPLACE_WITH_ACTUAL_SHA256"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/rich/rich-13.0.0.tar.gz"
    sha256 "REPLACE_WITH_ACTUAL_SHA256"
  end

  resource "cryptography" do
    url "https://files.pythonhosted.org/packages/cryptography/cryptography-42.0.0.tar.gz"
    sha256 "REPLACE_WITH_ACTUAL_SHA256"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "e3cli", shell_output("#{bin}/e3cli version")
  end
end
