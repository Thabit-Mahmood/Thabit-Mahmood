<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/credential-dark.svg">
    <img src="assets/credential-light.svg" width="100%" alt="Credential: Thabit Mahmood, security researcher and developer. PhD candidate, Multimedia University. Graduate Research Assistant, TM R&D. Focus: post-quantum cryptography, federated learning, intrusion detection. Based in Cyberjaya, Malaysia, from Egypt. Speaks Arabic and English. Signed with ML-DSA-65.">
  </picture>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/record-dark.svg">
    <img src="assets/record-light.svg" width="100%" alt="Fields of work. Research: my PhD makes federated learning verifiable and quantum-safe. Engineering: I build what I research, from protocol design to working code. Published: co-author of work on intrusion detection for drone networks, federated zero-day threat detection and deep learning for healthcare. Service: organising committees of academic conferences.">
  </picture>
</p>

<p align="center">
  <a href="https://www.linkedin.com/in/thabit-mahmood/"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/linkedin-dark.svg"><img src="assets/linkedin-light.svg" height="44" alt="LinkedIn"></picture></a>&nbsp;&nbsp;
  <a href="https://orcid.org/0009-0003-3909-3427"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/orcid-dark.svg"><img src="assets/orcid-light.svg" height="44" alt="ORCID"></picture></a>
</p>

<details>
<summary><b>Verify this profile</b></summary>
<br>

The credential is a real signed statement. [`identity/identity.json`](identity/identity.json) holds the facts on the card, signed with **ML-DSA-65** (FIPS 204, NIST's post-quantum signature standard). The public key and signature sit next to it. `verify.py` checks them with pyca/cryptography, or with the independent pure-Python dilithium-py if your cryptography predates ML-DSA. Change one character of the record and verification fails.

```sh
git clone https://github.com/Thabit-Mahmood/Thabit-Mahmood && cd Thabit-Mahmood
pip install --upgrade cryptography
python3 verify.py
```

</details>
