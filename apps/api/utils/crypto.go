package utils

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"fmt"
	"io"
)

// Encrypt encrypts plaintext using AES-256-GCM with the given key.
// The key is hashed with SHA-256 to ensure it is exactly 32 bytes.
// Returns a base64-encoded ciphertext string containing the nonce prepended to the encrypted data.
func Encrypt(plaintext, key string) (string, error) {
	if plaintext == "" {
		return "", nil
	}
	if key == "" {
		return "", fmt.Errorf("encryption key must not be empty")
	}

	// Derive a 32-byte key from the input using SHA-256.
	keyHash := sha256.Sum256([]byte(key))

	block, err := aes.NewCipher(keyHash[:])
	if err != nil {
		return "", fmt.Errorf("failed to create cipher: %w", err)
	}

	aesGCM, err := cipher.NewGCM(block)
	if err != nil {
		return "", fmt.Errorf("failed to create GCM: %w", err)
	}

	// Generate a random nonce.
	nonce := make([]byte, aesGCM.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return "", fmt.Errorf("failed to generate nonce: %w", err)
	}

	// Encrypt and prepend the nonce to the ciphertext.
	ciphertext := aesGCM.Seal(nonce, nonce, []byte(plaintext), nil)

	return base64.StdEncoding.EncodeToString(ciphertext), nil
}

// Decrypt decrypts a base64-encoded ciphertext produced by Encrypt.
func Decrypt(ciphertext, key string) (string, error) {
	if ciphertext == "" {
		return "", nil
	}
	if key == "" {
		return "", fmt.Errorf("decryption key must not be empty")
	}

	// Derive the same 32-byte key.
	keyHash := sha256.Sum256([]byte(key))

	data, err := base64.StdEncoding.DecodeString(ciphertext)
	if err != nil {
		return "", fmt.Errorf("failed to decode ciphertext: %w", err)
	}

	block, err := aes.NewCipher(keyHash[:])
	if err != nil {
		return "", fmt.Errorf("failed to create cipher: %w", err)
	}

	aesGCM, err := cipher.NewGCM(block)
	if err != nil {
		return "", fmt.Errorf("failed to create GCM: %w", err)
	}

	nonceSize := aesGCM.NonceSize()
	if len(data) < nonceSize {
		return "", fmt.Errorf("ciphertext too short")
	}

	nonce, encrypted := data[:nonceSize], data[nonceSize:]
	plaintext, err := aesGCM.Open(nil, nonce, encrypted, nil)
	if err != nil {
		return "", fmt.Errorf("failed to decrypt: %w", err)
	}

	return string(plaintext), nil
}

// MaskSecret masks a secret value, showing only the first 4 and last 4 characters.
// Values shorter than 10 characters are fully masked. Empty values return empty string.
func MaskSecret(value string) string {
	if value == "" {
		return ""
	}
	if len(value) < 10 {
		return "****"
	}
	return value[:4] + "..." + value[len(value)-4:]
}
