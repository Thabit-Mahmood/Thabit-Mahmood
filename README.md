<p align="center">
  <picture><source media="(prefers-color-scheme: dark)" srcset="assets/credential-dark.svg"><img src="assets/credential-light.svg" width="100%" alt="Credential: Thabit Mahmood, security researcher and developer. PhD candidate, Multimedia University. Graduate Research Assistant, TM R&D. Focus: post-quantum cryptography, federated learning, intrusion detection. Based in Cyberjaya, Malaysia, from Egypt. Speaks Arabic and English. Signed with ML-DSA-65 and re-verified daily."></picture>
</p>

<p align="center">
  <picture><source media="(prefers-color-scheme: dark)" srcset="assets/record-dark.svg"><img src="assets/record-light.svg" width="100%" alt="Fields of work. Research: federated learning that every participant can verify and that remains secure against quantum adversaries. Engineering: from protocol design to working code. Published research on intrusion detection for drone networks, federated zero-day threat detection and deep learning for healthcare. Service: committee member, 3rd International Conference on Emerging Trends and Innovation (ICETI, Springer). Handshakes: visitors can run a post-quantum handshake with this profile."></picture>
</p>

<p align="center">
  <a href="https://www.linkedin.com/in/thabit-mahmood/"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/linkedin-dark.svg"><img src="assets/linkedin-light.svg" height="44" alt="LinkedIn"></picture></a>&nbsp;&nbsp;
  <a href="https://orcid.org/0009-0003-3909-3427"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/orcid-dark.svg"><img src="assets/orcid-light.svg" height="44" alt="ORCID"></picture></a>&nbsp;&nbsp;
  <a href="https://github.com/Thabit-Mahmood/Thabit-Mahmood/issues/new?title=handshake&body=Submit%20this%20issue%20as%20it%20is.%20A%20GitHub%20Action%20will%20run%20a%20real%20ML-KEM-768%20key%20exchange%20with%20you%2C%20sign%20the%20transcript%20with%20ML-DSA-65%20and%20add%20you%20to%20the%20ledger.%0A%0AOptional%3A%20replace%20this%20paragraph%20with%20your%20own%20ML-KEM-768%20encapsulation%20key%20%281184%20bytes%20as%202368%20hex%20characters%29%20to%20get%20a%20ciphertext%20only%20you%20can%20decapsulate."><picture><source media="(prefers-color-scheme: dark)" srcset="assets/handshake-dark.svg"><img src="assets/handshake-light.svg" height="44" alt="Start a post-quantum handshake"></picture></a>
</p>

<details>
<summary><b>Verify this profile</b></summary>
<br>

The facts on the card live in [`identity/identity.json`](identity/identity.json), signed with **ML-DSA-65** (FIPS 204, NIST's post-quantum signature standard). Every handshake in [`identity/handshakes.json`](identity/handshakes.json) is signed by the same key. A GitHub Action re-checks all of it every day and redraws the card from the result, so the date under the seal is the last time it actually verified.

```sh
git clone https://github.com/Thabit-Mahmood/Thabit-Mahmood && cd Thabit-Mahmood
pip install --upgrade cryptography
python3 verify.py --handshakes
```

`verify.py` uses pyca/cryptography, or the independent pure-Python dilithium-py if your cryptography predates ML-DSA. Change one character of any record and verification fails.

</details>

<details>
<summary><b>How the handshake works</b></summary>
<br>

[Open an issue titled `handshake`](https://github.com/Thabit-Mahmood/Thabit-Mahmood/issues/new?title=handshake&body=Submit%20this%20issue%20as%20it%20is.%20A%20GitHub%20Action%20will%20run%20a%20real%20ML-KEM-768%20key%20exchange%20with%20you%2C%20sign%20the%20transcript%20with%20ML-DSA-65%20and%20add%20you%20to%20the%20ledger.%0A%0AOptional%3A%20replace%20this%20paragraph%20with%20your%20own%20ML-KEM-768%20encapsulation%20key%20%281184%20bytes%20as%202368%20hex%20characters%29%20to%20get%20a%20ciphertext%20only%20you%20can%20decapsulate.). A GitHub Action then:

1. takes your ML-KEM-768 encapsulation key from the issue if you pasted one, or makes an ephemeral key pair for you,
2. encapsulates a fresh 32-byte shared secret to it (ML-KEM-768, FIPS 203),
3. signs the transcript with this profile's ML-DSA-65 key and adds it to the ledger,
4. replies with the results and closes the issue.

Bring your own key and the reply includes the ciphertext; decapsulate it and the SHA-256 of your shared secret will match the signed commitment. One handshake per account.

The guilloché seal is drawn from the signing key's fingerprint, so a different key would draw a different seal.

</details>
