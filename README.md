<p align="center">
  <picture><source media="(prefers-color-scheme: dark)" srcset="assets/credential-dark.svg"><img src="assets/credential-light.svg" width="100%" alt="Credential: Thabit Mahmood, security researcher and developer. PhD candidate, Multimedia University. Graduate Research Assistant, TM R&D. Focus: post-quantum cryptography, federated learning, intrusion detection. Based in Cyberjaya, Malaysia. Signed with ML-DSA-65 and re-verified daily."></picture>
</p>

<p align="center">
  <picture><source media="(prefers-color-scheme: dark)" srcset="assets/record-dark.svg"><img src="assets/record-light.svg" width="100%" alt="Fields of work. Research: federated learning that every participant can verify and that remains secure against quantum adversaries. Engineering: from protocol design to working code. Published research on intrusion detection for drone networks, federated zero-day threat detection and deep learning for healthcare. Service: committee member, 3rd International Conference on Emerging Trends and Innovation (ICETI, Springer)."></picture>
</p>

<p align="center">
  <a href="https://www.linkedin.com/in/thabit-mahmood/"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/linkedin-dark.svg"><img src="assets/linkedin-light.svg" height="44" alt="LinkedIn"></picture></a>&nbsp;&nbsp;
  <a href="https://orcid.org/0009-0003-3909-3427"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/orcid-dark.svg"><img src="assets/orcid-light.svg" height="44" alt="ORCID"></picture></a>
</p>

<details>
<summary><b>Verify this profile</b></summary>
<br>

The facts on the card live in [`identity/identity.json`](identity/identity.json), signed with **ML-DSA-65** (FIPS 204, NIST's post-quantum signature standard). A GitHub Action re-checks it every day and redraws the card from the result, so the date under the seal is the last time it actually verified.

```sh
git clone https://github.com/Thabit-Mahmood/Thabit-Mahmood && cd Thabit-Mahmood
pip install --upgrade cryptography
python3 verify.py
```

`verify.py` uses pyca/cryptography, or the independent pure-Python dilithium-py if your cryptography predates ML-DSA. Change one character of the record and verification fails. The guilloché seal is drawn from the signing key's fingerprint, so a different key would draw a different seal.

</details>

