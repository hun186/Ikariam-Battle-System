# Barbarian Fleet icon provenance

Prepared on 2026-10-07 from the user-supplied Gameforge in-game Help screenshots captured on 2026-10-05. The unit artwork was cropped from the official Help panels, the surrounding Help UI/background was removed, and the result was stored as compact local WebP assets for the simulator. Runtime code uses only these committed local files.

The repository does not claim ownership of, or an open-source license for, the Ikariam artwork. The source screenshots are evidence supplied by the user from the official in-game Help.

| Unit | Official Help screenshot | Local path | SHA-256 |
| --- | --- | --- | --- |
| Deckwrecker | `image(20261005-030555).png` | `assets/unit-icons/barbarian-fleet/barbarian_deckwrecker.webp` | `d8965dfedcbf2b3e6b6171f7232c0e38d5851386caf4b467d63f58300b0a2bf5` |
| Sail Shredder | `image(20261005-030617).png` | `assets/unit-icons/barbarian-fleet/barbarian_sail_shredder.webp` | `0e78d10fe7776a61e983f75344d12a89db63da54a3f0b5ce28ed577e6187e724` |
| Pyroboat | `image(20261005-030620).png` | `assets/unit-icons/barbarian-fleet/barbarian_pyroboat.webp` | `355410b947adf2603f1587bf54e938f535302744c3479d7125be83f95939ff50` |
| Boulder Catapult | `image(20261005-030634).png` | `assets/unit-icons/barbarian-fleet/barbarian_boulder_catapult.webp` | `285107022c2d8e78afc82b0aa8d5f999d983a429b5abcac4ea8a2e13f2ad33fc` |
| Wedge Paddler | `image(20261005-030646).png` | `assets/unit-icons/barbarian-fleet/barbarian_wedge_paddler.webp` | `135a1605f7f8f9e438ff3cfcbd7524a50f258f2e96e6b62ac088d9ba71d179e2` |
| Powder Pitcher | `image(20261005-030704).png` | `assets/unit-icons/barbarian-fleet/barbarian_powder_pitcher.webp` | `f8f513b897847bdc3c5ccf63dc0876dbccc82c8ed57a41a228b3523c3b2fd78f` |
| Terror of the Deep | `image(20261005-030717).png` | `assets/unit-icons/barbarian-fleet/barbarian_terror_of_the_deep.webp` | `8d73ca0ddb7105adf1e6fb85ae8a33b1a0a9026d9aca1d9ade0deb0a6f1931cc` |
| Dragonfire | `image(20261005-030735).png` | `assets/unit-icons/barbarian-fleet/barbarian_dragonfire.webp` | `9cf2bb6b6df02d860c84b2caac59cc842705e2d4c70f75093157d5aa3de7a4e2` |
| Dirigible Igniter | `image(20261005-030746).png` | `assets/unit-icons/barbarian-fleet/barbarian_dirigible_igniter.webp` | `eed367ee0480394c030cf8f3c40a60cbc01fd86603b72aaf3d63c9fa74e25488` |
| Barbarian Nest | `image(20261005-030758).png` | `assets/unit-icons/barbarian-fleet/barbarian_nest.webp` | `7bc44cada59bcc140cb87226bf1ea3d9081221ea17f174eb56f37b00cc06f25c` |

The same asset bytes are mirrored under `public/assets/unit-icons/barbarian-fleet/` because the repository maintains both root and public static-entry copies.

Review cleanup: Wedge Paddler, Terror of the Deep, and Dragonfire were regenerated on 2026-10-07 from the original PNG Help screenshots, with the Help-panel border removed before a fresh Pillow/libwebp WebP encode. The regenerated files were locally decoded successfully before commit; the table above records the hashes of those committed bytes.
