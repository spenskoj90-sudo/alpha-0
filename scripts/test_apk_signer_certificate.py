import unittest
from apk_signer_certificate import certificate_digests

S256 = "a" * 64
S1 = "b" * 40

class CertificateReportTest(unittest.TestCase):
    def test_build_tools_37_v2(self):
        r = f"V2 Signer: certificate SHA-256 digest: {S256}\nV2 Signer: certificate SHA-1 digest: {S1}\n"
        self.assertEqual(certificate_digests(r), {"sha256": S256, "sha1": S1})

    def test_legacy_format(self):
        r = f"Signer #1 certificate SHA-256 digest: {S256}\nSigner #1 certificate SHA-1 digest: {S1}"
        self.assertEqual(certificate_digests(r)["sha1"], S1)

    def test_same_certificate_across_schemes(self):
        r = "".join(f"V{i} Signer: certificate SHA-256 digest: {S256}\n" for i in (1, 2, 3))
        self.assertEqual(certificate_digests(r)["sha256"], S256)

    def test_multi_signer_rejected(self):
        r = f"V2 Signer: certificate SHA-256 digest: {S256}\nV2 Signer #2: certificate SHA-256 digest: {'c'*64}"
        with self.assertRaises(ValueError):
            certificate_digests(r)

    def test_empty_malformed_unknown_rejected(self):
        for r in ("", "V2 Signer: certificate SHA-256 digest: bad", f"Other: certificate SHA-256 digest: {S256}", "x"*32769):
            with self.subTest(r=r[:20]), self.assertRaises(ValueError):
                certificate_digests(r)
