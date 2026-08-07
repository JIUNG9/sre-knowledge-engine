package utils

import (
	"encoding/base64"
	"strings"
	"testing"
)

const testKey = "a-test-encryption-key-not-a-real-secret"

func TestEncryptDecryptRoundTrip(t *testing.T) {
	cases := []struct {
		name      string
		plaintext string
	}{
		{"short", "hunter2"},
		{"aws secret shaped", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"},
		{"unicode", "비밀 값 — with an em dash"},
		{"whitespace only", "   "},
		{"json blob", `{"token":"abc","nested":{"n":1}}`},
		{"long", strings.Repeat("payload-", 4096)},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			ct, err := Encrypt(tc.plaintext, testKey)
			if err != nil {
				t.Fatalf("Encrypt: %v", err)
			}
			if ct == tc.plaintext {
				t.Fatal("ciphertext equals plaintext — nothing was encrypted")
			}
			got, err := Decrypt(ct, testKey)
			if err != nil {
				t.Fatalf("Decrypt: %v", err)
			}
			if got != tc.plaintext {
				t.Errorf("round trip mismatch:\n got %q\nwant %q", got, tc.plaintext)
			}
		})
	}
}

// The nonce must be fresh per call. If it weren't, identical plaintexts would
// produce identical ciphertexts and an observer could tell that two stored
// secrets are the same value without decrypting either.
func TestEncryptIsNotDeterministic(t *testing.T) {
	const plaintext = "same-input-every-time"
	seen := make(map[string]struct{}, 32)
	for i := 0; i < 32; i++ {
		ct, err := Encrypt(plaintext, testKey)
		if err != nil {
			t.Fatalf("Encrypt: %v", err)
		}
		if _, dup := seen[ct]; dup {
			t.Fatalf("ciphertext repeated on iteration %d — nonce is not unique per call", i)
		}
		seen[ct] = struct{}{}
	}
}

func TestDecryptRejectsWrongKey(t *testing.T) {
	ct, err := Encrypt("confidential", testKey)
	if err != nil {
		t.Fatalf("Encrypt: %v", err)
	}
	got, err := Decrypt(ct, testKey+"-different")
	if err == nil {
		t.Fatalf("expected an error with the wrong key, got plaintext %q", got)
	}
	if got != "" {
		t.Errorf("no plaintext should be returned on failure, got %q", got)
	}
}

// GCM is authenticated encryption; flipping any bit of the payload must fail the
// tag check rather than return mangled plaintext. This is the property that makes
// GCM the right choice here, so it is worth asserting explicitly.
func TestDecryptRejectsTamperedCiphertext(t *testing.T) {
	ct, err := Encrypt("do-not-modify-me", testKey)
	if err != nil {
		t.Fatalf("Encrypt: %v", err)
	}
	raw, err := base64.StdEncoding.DecodeString(ct)
	if err != nil {
		t.Fatalf("decode: %v", err)
	}

	for _, pos := range []int{0, len(raw) / 2, len(raw) - 1} {
		tampered := make([]byte, len(raw))
		copy(tampered, raw)
		tampered[pos] ^= 0x01

		if _, err := Decrypt(base64.StdEncoding.EncodeToString(tampered), testKey); err == nil {
			t.Errorf("flipping a bit at offset %d was accepted; GCM tag not enforced", pos)
		}
	}
}

func TestDecryptRejectsMalformedInput(t *testing.T) {
	ct, err := Encrypt("x", testKey)
	if err != nil {
		t.Fatalf("Encrypt: %v", err)
	}
	raw, _ := base64.StdEncoding.DecodeString(ct)

	cases := []struct {
		name  string
		input string
	}{
		{"not base64", "this is not base64 !!!"},
		// Shorter than the 12-byte GCM nonce, so it can't even be split.
		{"shorter than nonce", base64.StdEncoding.EncodeToString(raw[:4])},
		{"nonce only, no payload", base64.StdEncoding.EncodeToString(raw[:12])},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if _, err := Decrypt(tc.input, testKey); err == nil {
				t.Error("expected an error, got nil")
			}
		})
	}
}

// Documented behaviour: an empty value passes through rather than erroring, so a
// caller storing an optional secret doesn't have to special-case it.
func TestEmptyValuePassesThrough(t *testing.T) {
	if ct, err := Encrypt("", testKey); err != nil || ct != "" {
		t.Errorf("Encrypt(\"\") = (%q, %v), want (\"\", nil)", ct, err)
	}
	if pt, err := Decrypt("", testKey); err != nil || pt != "" {
		t.Errorf("Decrypt(\"\") = (%q, %v), want (\"\", nil)", pt, err)
	}
}

func TestEmptyKeyIsRejected(t *testing.T) {
	if _, err := Encrypt("something", ""); err == nil {
		t.Error("Encrypt with empty key should fail")
	}
	if _, err := Decrypt("something", ""); err == nil {
		t.Error("Decrypt with empty key should fail")
	}
}

func TestMaskSecret(t *testing.T) {
	cases := []struct {
		name  string
		value string
		want  string
	}{
		{"empty", "", ""},
		{"single char", "x", "****"},
		{"nine chars is fully masked", "123456789", "****"},
		{"ten chars is the boundary", "1234567890", "1234...7890"},
		{"long token", "AKIAIOSFODNN7EXAMPLE", "AKIA...MPLE"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := MaskSecret(tc.value); got != tc.want {
				t.Errorf("MaskSecret(%q) = %q, want %q", tc.value, got, tc.want)
			}
		})
	}
}

// The point of masking is that the middle never reaches a log line.
func TestMaskSecretDoesNotLeakTheMiddle(t *testing.T) {
	const secret = "AKIA" + "SUPERSECRETMIDDLE" + "1234"
	masked := MaskSecret(secret)
	if strings.Contains(masked, "SUPERSECRETMIDDLE") {
		t.Fatalf("masked value leaked the middle: %q", masked)
	}
	if len(masked) >= len(secret) {
		t.Errorf("masked value %q is not shorter than the input", masked)
	}
}
