# Migração pública do núcleo C4.4

Este manifesto registra o recorte operacional; não cria novo congelamento. Os SHA-256 são de arquivos de trabalho. O documento original de congelamento está em `cycles/c4_4_technical_code_freeze.md`. Arquivos históricos, gravações, modelos, perfis e dados permanecem na origem ou armazenamento privado.

Os dois módulos derivados de personalização mantêm apenas constantes e funções utilizadas pelo runtime; a pesquisa histórica fica na origem. A comparação das árvores sintáticas das oito definições preservadas passou, assim como os testes sintéticos. Os testes e documentação de perfil usam identificador sintético. O teste de reprodução é derivado para separar documentação privada de testes públicos. `.gitattributes` acrescenta regras específicas para os oito arquivos cuja integridade o R4 valida.

Os manifestos privados R4 e GV2.9 não são incluídos. Os dois R4 devem ser fornecidos em `ai/docs/cycles/` somente em ambiente local autorizado, nos nomes esperados pelo código e ignorados pelo Git. A verificação original continua obrigatória e falha se ausente ou divergente. Artefatos necessários e hashes: `c44_live_tester_reproducibility.md`. A publicação ou redistribuição desses artefatos depende de permissão, licença, consentimento e controle de acesso.

A instalação em máquina limpa não foi verificada; não há lockfile resolvido e validado para um ambiente independente. A regressão histórica de 3154 PASS / 2 SKIP ocorreu no projeto de origem, não neste recorte. Não representa integração com app ou hardware. Os testes privados opcionais não são PASS quando ausentes.

| Caminho em ai | SHA-256 de origem ou arquivo estrutural anterior | SHA-256 público | Estado |
| --- | --- | --- | --- |
| `.flake8` | `692f720d348441d9728a9a8500a4bca9e226e4a2c18972f55a1df0d0fd2f05f7` | `692f720d348441d9728a9a8500a4bca9e226e4a2c18972f55a1df0d0fd2f05f7` | idêntico |
| `.gitattributes` | `c2a868f2be0857d38bfcdf9fdbb8f9f308ae9cff32ea5258259a6ca47b77831c` | `ae595a39daa18db5683a236a2c53c4cc34b9f47247b8d3bf5f9b4f8faef61bc2` | derivado |
| `.gitignore` | `7cb3c5914b80304778c31548ebd0d357d6c09861c76b0098d0c552435589fd41` | `5775a6855c40b159b4eedffa14cd0162183cb6f3126b732007ca95a7cb11850c` | derivado |
| `README.md` | `f04997def219ecc205d3dc3a9ea8d2f4d4eab9424d04bbebd5ea633ef5e76ffd` | `392212b2db71af48da233f337e87efefe99c788060e07454b3f81c70e95d61d4` | derivado |
| `docs/c44_live_tester_reproducibility.md` | `00f16338a3af2fdbe7b75851d4062a61dc5e8a7081a3f598d1267f9b97dbef44` | `00f16338a3af2fdbe7b75851d4062a61dc5e8a7081a3f598d1267f9b97dbef44` | idêntico |
| `docs/cycles/c4_4_technical_code_freeze.md` | `aef0e6493410f70a975250831df8b7a20244ffa9ad4d9aa7b3f49eed63d75782` | `aef0e6493410f70a975250831df8b7a20244ffa9ad4d9aa7b3f49eed63d75782` | idêntico |
| `docs/cycles/multispeaker_visual_01_temporal_policy_v2.json` | `4680a3fb47866d470fb98223c8f8d654d19150905d4ba7289096e80d8a6f39a1` | `4680a3fb47866d470fb98223c8f8d654d19150905d4ba7289096e80d8a6f39a1` | idêntico |
| `docs/cycles/rejection_4_edge_policy_freeze.json` | `cf9c2976698e515c468567961783aad885dcafba86ec0cbcebaa49c71c6df4e9` | `cf9c2976698e515c468567961783aad885dcafba86ec0cbcebaa49c71c6df4e9` | idêntico |
| `docs/cycles/rejection_4_edge_policy_manifest.json` | `cf10de54fb136d79287863950de3e69dc4ef20442ace7e9d2f8f8716c39c9cd4` | `cf10de54fb136d79287863950de3e69dc4ef20442ace7e9d2f8f8716c39c9cd4` | idêntico |
| `docs/cycles/rejection_4_reference_freeze.json` | `79015c1b7f39ae64027a1a69253ba0411cdb8351a339d0a687d0ec4e75714a3c` | `79015c1b7f39ae64027a1a69253ba0411cdb8351a339d0a687d0ec4e75714a3c` | idêntico |
| `docs/global_live_visual_tester.md` | `42afd51c9ee21e547c98f20d3e3917abcc8519de0797e3e6854a43ca7937e381` | `20b6e4b8fefff58c2f73ee1e904d41840c43292ee34d033a0bc13c3daeddffe2` | derivado |
| `pyproject.toml` | `fbe1f9beccc02068a4256d4a03d2322404ec8e5e6be071fcae85d58dca44bc78` | `fbe1f9beccc02068a4256d4a03d2322404ec8e5e6be071fcae85d58dca44bc78` | idêntico |
| `scripts/dataset/capture_cycle_06_heldout_raw.py` | `059309701611893e511ce6441edbb9e957d8e1fedc2ef939f244524c27e04100` | `059309701611893e511ce6441edbb9e957d8e1fedc2ef939f244524c27e04100` | idêntico |
| `scripts/dataset/collect_visual_session.py` | `d1f042e2571756c3d510613026cf9288e9b27aa48d6c932a3a6be1ecbf9ffc6d` | `d1f042e2571756c3d510613026cf9288e9b27aa48d6c932a3a6be1ecbf9ffc6d` | idêntico |
| `scripts/dataset/qc_cycle_06_new_heldout.py` | `e1846245bb4d3e56afee34ec522311e1d74cb2fc86b7da9e58a6390124cd91a2` | `e1846245bb4d3e56afee34ec522311e1d74cb2fc86b7da9e58a6390124cd91a2` | idêntico |
| `scripts/demo/__init__.py` | `e71527d82048ac1c503c070196e54a6cf91b5492b4d415e66e2766d1ae72124c` | `e71527d82048ac1c503c070196e54a6cf91b5492b4d415e66e2766d1ae72124c` | idêntico |
| `scripts/demo/capture_rejection_4_heldout.py` | `7a44d847ef6760f6fab8c6bdc6d9011d02170e751ecd24d7a329a7dc0654b8a6` | `7a44d847ef6760f6fab8c6bdc6d9011d02170e751ecd24d7a329a7dc0654b8a6` | idêntico |
| `scripts/demo/global_live_visual_tester.py` | `f892a9da70b055fa7fb746543600183ed8a17e08347404a6cb3b4dd8eafb2259` | `f892a9da70b055fa7fb746543600183ed8a17e08347404a6cb3b4dd8eafb2259` | idêntico |
| `scripts/demo/live_visual_tester.py` | `78ade56aaa3cd7bfb14c4ebce844d19cef978eb8bfa24144f10c9cc02f2e22bd` | `78ade56aaa3cd7bfb14c4ebce844d19cef978eb8bfa24144f10c9cc02f2e22bd` | idêntico |
| `scripts/demo/msv_temporal_capture.py` | `986f7a0372ce132d99dfc3c2020fcbc0daac3a9719913c61d957b16d2acfcef3` | `986f7a0372ce132d99dfc3c2020fcbc0daac3a9719913c61d957b16d2acfcef3` | idêntico |
| `scripts/evaluation/evaluate_cycle_06_edge_feasibility.py` | `d953464e7503e76e5a19494cb5a22fa4a28340e2fdca495c6b3ca72dc1bb1f41` | `d953464e7503e76e5a19494cb5a22fa4a28340e2fdca495c6b3ca72dc1bb1f41` | idêntico |
| `scripts/evaluation/qc_rejection_3_heldout.py` | `311e33c7344cc3ddeec09b068d7026632ecf129cab311108f523c11ee0422b89` | `311e33c7344cc3ddeec09b068d7026632ecf129cab311108f523c11ee0422b89` | idêntico |
| `scripts/evaluation/qc_rejection_4_heldout.py` | `5ba0b67aaacfb3764e0c92dcf48801e409ee2f63f37f3069aabfdfe6cedcef1f` | `5ba0b67aaacfb3764e0c92dcf48801e409ee2f63f37f3069aabfdfe6cedcef1f` | idêntico |
| `src/silent_voice/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | idêntico |
| `src/silent_voice/audio/__init__.py` | `942ae9118406f4b1a6cf91f5ffc8a4439a00c016517471125ff99b67d171cbf2` | `942ae9118406f4b1a6cf91f5ffc8a4439a00c016517471125ff99b67d171cbf2` | idêntico |
| `src/silent_voice/audio/context_interpreter.py` | `d025c5391079405895a7c3a6008ce1d67de4ba3750f61834ebb3c6b941667f86` | `d025c5391079405895a7c3a6008ce1d67de4ba3750f61834ebb3c6b941667f86` | idêntico |
| `src/silent_voice/audio/contextual_audio.py` | `b776e53b70eaa637c20acab6258e845db482633a1b5df3ba3e91bad517ebc1e9` | `b776e53b70eaa637c20acab6258e845db482633a1b5df3ba3e91bad517ebc1e9` | idêntico |
| `src/silent_voice/edge/__init__.py` | `0a25825ffceee7f810e728e819661624f55c492e491cf9f2fa306f4b61f8ab33` | `0a25825ffceee7f810e728e819661624f55c492e491cf9f2fa306f4b61f8ab33` | idêntico |
| `src/silent_voice/edge/cycle_06_final_heldout.py` | `f1bc2981b39a99770be4786edbc78ac4823b04b6cb690b76dc48e72d71d83354` | `f1bc2981b39a99770be4786edbc78ac4823b04b6cb690b76dc48e72d71d83354` | idêntico |
| `src/silent_voice/edge/landmark_gap_runtime.py` | `5aa29c65a2abe2e90a352c50f862ad3ce27d7757b268c39bb960d5b355f1a51d` | `5aa29c65a2abe2e90a352c50f862ad3ce27d7757b268c39bb960d5b355f1a51d` | idêntico |
| `src/silent_voice/edge/parity.py` | `707583e679a9dce1ba63156e985ab0bb3a5124d55e4c4b3065ad0005084ebb0e` | `707583e679a9dce1ba63156e985ab0bb3a5124d55e4c4b3065ad0005084ebb0e` | idêntico |
| `src/silent_voice/edge/preheldout_freeze.py` | `fcbbc7678aec4d55936e2dc44538af4933a08ac4f5ebf21d422ede0402585652` | `fcbbc7678aec4d55936e2dc44538af4933a08ac4f5ebf21d422ede0402585652` | idêntico |
| `src/silent_voice/edge/rejection_3_edge_parity.py` | `4f9b1dc048703d405a477745c4b5c11c77b3343817b50be339068bfc357c4a75` | `4f9b1dc048703d405a477745c4b5c11c77b3343817b50be339068bfc357c4a75` | idêntico |
| `src/silent_voice/edge/rejection_3_final_heldout.py` | `f45f77996efa817566b2b751957c2ab8caea9d9b5d1b8adaa89d35adda758b25` | `f45f77996efa817566b2b751957c2ab8caea9d9b5d1b8adaa89d35adda758b25` | idêntico |
| `src/silent_voice/edge/rejection_4_final_heldout.py` | `278cf889297313c74cf5365535ba8a78d551b03bfd2918ab2f95f7052de44900` | `278cf889297313c74cf5365535ba8a78d551b03bfd2918ab2f95f7052de44900` | idêntico |
| `src/silent_voice/edge/swinlip_export.py` | `6f8d3f1eac4f3bcbb2e8d376ba19db978a601474e64ddb07492f321d73b6ede9` | `6f8d3f1eac4f3bcbb2e8d376ba19db978a601474e64ddb07492f321d73b6ede9` | idêntico |
| `src/silent_voice/fusion/context_advisory.py` | `8b8db6ed7294e721103c75264238266ffd12bfe41ad80f152bb7927c5814b8f7` | `8b8db6ed7294e721103c75264238266ffd12bfe41ad80f152bb7927c5814b8f7` | idêntico |
| `src/silent_voice/inference/__init__.py` | `87cb45331e05a6809f14232bdbee3aee8b8cd68ee3e64d74b8ed428020bd089d` | `87cb45331e05a6809f14232bdbee3aee8b8cd68ee3e64d74b8ed428020bd089d` | idêntico |
| `src/silent_voice/inference/global_live_visual_tester.py` | `5dd3d2bf7578ef94b11f67b46178a759bc4341c4d9bddcfce8c03c35e75dd1ae` | `5dd3d2bf7578ef94b11f67b46178a759bc4341c4d9bddcfce8c03c35e75dd1ae` | idêntico |
| `src/silent_voice/inference/global_live_visual_tester_window.py` | `e74295a64e465dffa8005e0c2863badc177b10abfe3e342f3023b86928a4a0d3` | `e74295a64e465dffa8005e0c2863badc177b10abfe3e342f3023b86928a4a0d3` | idêntico |
| `src/silent_voice/inference/live_context_session.py` | `73f70a468be1755502c873daecd267541e5aeecdc65900228f42973b6efcaeae` | `73f70a468be1755502c873daecd267541e5aeecdc65900228f42973b6efcaeae` | idêntico |
| `src/silent_voice/inference/live_fps_diagnostic.py` | `fd2521fcd2d90557d77d6e83ccf60977b7bfc4c7fbce55a69fb7c5ced47e5d12` | `fd2521fcd2d90557d77d6e83ccf60977b7bfc4c7fbce55a69fb7c5ced47e5d12` | idêntico |
| `src/silent_voice/inference/live_visual_tester.py` | `f9ec0592c4171646e99eefc2194d28bfe3b1ea0b3b49ec5c1ba9893b0ec0615e` | `f9ec0592c4171646e99eefc2194d28bfe3b1ea0b3b49ec5c1ba9893b0ec0615e` | idêntico |
| `src/silent_voice/inference/personal_live_visual_tester.py` | `5e96dae6c2b8938c989edb5e065f6a9f7d18b32fe03e7eaf9a5e8cee715343a9` | `5e96dae6c2b8938c989edb5e065f6a9f7d18b32fe03e7eaf9a5e8cee715343a9` | idêntico |
| `src/silent_voice/models/compact_tcn.py` | `f2897b8dc993075fd0644ab4f76b01d0cd8b8ba2c12818a099e3538add7c03fd` | `f2897b8dc993075fd0644ab4f76b01d0cd8b8ba2c12818a099e3538add7c03fd` | idêntico |
| `src/silent_voice/models/compact_tcn_config.py` | `8a00589f054a473e0ef2d720c39cffa7170678d74b0f3dde0a2a0a367ce36b42` | `8a00589f054a473e0ef2d720c39cffa7170678d74b0f3dde0a2a0a367ce36b42` | idêntico |
| `src/silent_voice/models/compact_tcn_training.py` | `831536568738d4038c816aac3172d596fd2d51ac3894e2848232a7343c8cfccc` | `831536568738d4038c816aac3172d596fd2d51ac3894e2848232a7343c8cfccc` | idêntico |
| `src/silent_voice/rejection/__init__.py` | `e1abdb6ec0bdfa8fbe36eff85ee69bf25828fe8e7ab2bf7ca88f8e01ab7ce502` | `e1abdb6ec0bdfa8fbe36eff85ee69bf25828fe8e7ab2bf7ca88f8e01ab7ce502` | idêntico |
| `src/silent_voice/rejection/hybrid_rejection_final.py` | `3176caae19f7c551e6cec0724fd8d67090f6f6215f6b0841a96ee60844c370dc` | `3176caae19f7c551e6cec0724fd8d67090f6f6215f6b0841a96ee60844c370dc` | idêntico |
| `src/silent_voice/rejection/hybrid_rejection_nested_loso.py` | `154e13f6005973e8a2711b9ed8208b4cece5305a724b9872412efc54931f1db6` | `154e13f6005973e8a2711b9ed8208b4cece5305a724b9872412efc54931f1db6` | idêntico |
| `src/silent_voice/rejection/hybrid_rejection_scores.py` | `7413530c94c4d62cec5aabca12792df5bc8493c957101979b34e9839655bd65d` | `7413530c94c4d62cec5aabca12792df5bc8493c957101979b34e9839655bd65d` | idêntico |
| `src/silent_voice/rejection/rejection_3_diagnostics.py` | `aa58870c726ea3410bcf7d52030261b3506fce875e814aa61215a3dabd78b40b` | `aa58870c726ea3410bcf7d52030261b3506fce875e814aa61215a3dabd78b40b` | idêntico |
| `src/silent_voice/rejection/rejection_3_final_calibration.py` | `5170a775375f4423c46f81bd6d151fa434b18af53410f29b180a041c9730f794` | `5170a775375f4423c46f81bd6d151fa434b18af53410f29b180a041c9730f794` | idêntico |
| `src/silent_voice/rejection/rejection_3_heldout_plan.py` | `bc50da55edad4dbd9e5ade13ca658e03481b335bbe0ea02f14b328022fe343d8` | `bc50da55edad4dbd9e5ade13ca658e03481b335bbe0ea02f14b328022fe343d8` | idêntico |
| `src/silent_voice/rejection/rejection_3_nested_selection.py` | `afc71ed542debc39063325ef89cf2aafb9fd6e785bc219cd04fad7bd549667d1` | `afc71ed542debc39063325ef89cf2aafb9fd6e785bc219cd04fad7bd549667d1` | idêntico |
| `src/silent_voice/rejection/rejection_3_scores.py` | `848c4dc834bb252f89fa31fe85565cd5832c6a7facec0978d2950d3f9ad3e25a` | `848c4dc834bb252f89fa31fe85565cd5832c6a7facec0978d2950d3f9ad3e25a` | idêntico |
| `src/silent_voice/rejection/rejection_4_heldout_plan.py` | `ccad43381583f60ef0ee87b2e03bf0cdf82cf12ca0015be324829f25a7b41d63` | `ccad43381583f60ef0ee87b2e03bf0cdf82cf12ca0015be324829f25a7b41d63` | idêntico |
| `src/silent_voice/rejection/rejection_capture_snapshot.py` | `e2af071423e40facb21ee3beae1f5e0b6633e2f9634855c83101c45f3d946bfb` | `e2af071423e40facb21ee3beae1f5e0b6633e2f9634855c83101c45f3d946bfb` | idêntico |
| `src/silent_voice/rejection/rejection_dataset.py` | `29d4c64f88ad5830c67291fc6bf7ccb9fe61bf6f0f2c92cd7b0fbb7c8876a8c0` | `29d4c64f88ad5830c67291fc6bf7ccb9fe61bf6f0f2c92cd7b0fbb7c8876a8c0` | idêntico |
| `src/silent_voice/rejection/rejection_metrics.py` | `90cf08d3e5458772f355f606bb6ac8e74c379395518777debe138aa9b15dea8e` | `90cf08d3e5458772f355f606bb6ac8e74c379395518777debe138aa9b15dea8e` | idêntico |
| `src/silent_voice/rejection/rejection_protocol.py` | `e1bcfc6042f79abcd80e69076e5ee01914f9a281c989ee8bb4e6e1442ab98a53` | `e1bcfc6042f79abcd80e69076e5ee01914f9a281c989ee8bb4e6e1442ab98a53` | idêntico |
| `src/silent_voice/vision/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | idêntico |
| `src/silent_voice/vision/dataset_collection_plan.py` | `d59ec56be7654a7e572740142ef499a17df86f7108064a9a97b993cecf58c6a3` | `d59ec56be7654a7e572740142ef499a17df86f7108064a9a97b993cecf58c6a3` | idêntico |
| `src/silent_voice/vision/detector.py` | `16899ae8eda3b1d70f12d87f1601e83901e33ae1f599983726ec5c9188dcaa27` | `16899ae8eda3b1d70f12d87f1601e83901e33ae1f599983726ec5c9188dcaa27` | idêntico |
| `src/silent_voice/vision/dtw_tcn_comparison.py` | `ab58a1debb00f5eae00503f80c9dcd654a6fd9c4fd11e2cc89eb29e508ff46b0` | `ab58a1debb00f5eae00503f80c9dcd654a6fd9c4fd11e2cc89eb29e508ff46b0` | idêntico |
| `src/silent_voice/vision/dtw_tcn_error_analysis.py` | `f2a2ac0b506be6749cb8779aba100996432fc4eb42021b3aadb1f19611e3fd69` | `f2a2ac0b506be6749cb8779aba100996432fc4eb42021b3aadb1f19611e3fd69` | idêntico |
| `src/silent_voice/vision/dtw_tcn_predictions.py` | `d246006c19707659642e32b6ce8dce29d34b31a1d1110c8a6b81b384dc01d6ef` | `d246006c19707659642e32b6ce8dce29d34b31a1d1110c8a6b81b384dc01d6ef` | idêntico |
| `src/silent_voice/vision/feature_sample.py` | `859bb36f56889235ec4b87287fa1ae78f93be0676a8c2fa45f88a6c8a455e3a8` | `859bb36f56889235ec4b87287fa1ae78f93be0676a8c2fa45f88a6c8a455e3a8` | idêntico |
| `src/silent_voice/vision/feature_sample_builder.py` | `c001fbe1455ba976d049db3a41c13da08cb9a19c42c95720fe3ac4f07eb1978c` | `c001fbe1455ba976d049db3a41c13da08cb9a19c42c95720fe3ac4f07eb1978c` | idêntico |
| `src/silent_voice/vision/feature_sample_storage.py` | `150293aa822e68a7b2bdff1a8438056c5a7120c069aae234a64c505bca9184ce` | `150293aa822e68a7b2bdff1a8438056c5a7120c069aae234a64c505bca9184ce` | idêntico |
| `src/silent_voice/vision/hybrid_features.py` | `d7e69e829554525bb74990aa16703b5c6ed79874d29234830f4137ec620675f5` | `d7e69e829554525bb74990aa16703b5c6ed79874d29234830f4137ec620675f5` | idêntico |
| `src/silent_voice/vision/hybrid_linear_probe.py` | `f3b08ee5c420d16cca902ef4f25b82011370cbdecdd03cc1d1a1d160fb996d30` | `f3b08ee5c420d16cca902ef4f25b82011370cbdecdd03cc1d1a1d160fb996d30` | idêntico |
| `src/silent_voice/vision/hybrid_loso.py` | `bd6364c81fe283e965e62422e977d0e7ed3dfa3230b58596e865e8c7623cb351` | `bd6364c81fe283e965e62422e977d0e7ed3dfa3230b58596e865e8c7623cb351` | idêntico |
| `src/silent_voice/vision/landmark_gap.py` | `85e742687ebbba236a543fa5eb1bf45c787111451087dc97d3dda0e104991c4a` | `85e742687ebbba236a543fa5eb1bf45c787111451087dc97d3dda0e104991c4a` | idêntico |
| `src/silent_voice/vision/landmarks.py` | `90f057bca71c357c65a383e25be9793387cf198f5817853d16171c08ea569e63` | `90f057bca71c357c65a383e25be9793387cf198f5817853d16171c08ea569e63` | idêntico |
| `src/silent_voice/vision/legacy_weighted_dtw.py` | `58b2a2951d478dc61b6f25a332efe0f6f84f8d801c5c800234521ff2301da49f` | `58b2a2951d478dc61b6f25a332efe0f6f84f8d801c5c800234521ff2301da49f` | idêntico |
| `src/silent_voice/vision/legacy_weighted_dtw_loso.py` | `39484c0f53c6a06d40591144676f53f09be29790e77d0b96884b43587d9234f8` | `39484c0f53c6a06d40591144676f53f09be29790e77d0b96884b43587d9234f8` | idêntico |
| `src/silent_voice/vision/mouth_roi_dataset.py` | `1538b13756b98f21a9aa7e4ef7014e0ffef27884256c0567cf7f7514c56451d6` | `1538b13756b98f21a9aa7e4ef7014e0ffef27884256c0567cf7f7514c56451d6` | idêntico |
| `src/silent_voice/vision/normalization.py` | `1eebd45cf9e856437adff512096437eae97ede467042f6bba2fc3153d9b735dd` | `1eebd45cf9e856437adff512096437eae97ede467042f6bba2fc3153d9b735dd` | idêntico |
| `src/silent_voice/vision/personalization_development_protocol.py` | `386c626ebba6d0fa864b21ae8168f2a63acc23d899a5bf8dc78619f52e06f997` | `7ce5847b4d80179db151d2210911800d574a3e54caace11571110dd2d5566f8a` | derivado |
| `src/silent_voice/vision/pipeline.py` | `7367bd47d52ba9b9079b8768c956ce70135d1e2fd054018fc529051337a81fd6` | `7367bd47d52ba9b9079b8768c956ce70135d1e2fd054018fc529051337a81fd6` | idêntico |
| `src/silent_voice/vision/positive_classifier_final.py` | `a49abf6ed942244c77314104922d45091ec5edb7c71e6469aba084a2988ca9f9` | `a49abf6ed942244c77314104922d45091ec5edb7c71e6469aba084a2988ca9f9` | idêntico |
| `src/silent_voice/vision/rejection_visual_features.py` | `90c541d3c78e66567f49357c29ddc14f6dfd551f7211277e40a5fb2487cd44f7` | `90c541d3c78e66567f49357c29ddc14f6dfd551f7211277e40a5fb2487cd44f7` | idêntico |
| `src/silent_voice/vision/strong_dtw_classifier.py` | `639326815590a278335bd7f7612ba402d23c71ad2d281d10415d69bb3d4f8826` | `639326815590a278335bd7f7612ba402d23c71ad2d281d10415d69bb3d4f8826` | idêntico |
| `src/silent_voice/vision/strong_dtw_distance.py` | `0afd8acd67f7d9dd956a523e5dda4a9c3b1be2e13b5b2b0e1c74e274a5cd1b71` | `0afd8acd67f7d9dd956a523e5dda4a9c3b1be2e13b5b2b0e1c74e274a5cd1b71` | idêntico |
| `src/silent_voice/vision/strong_dtw_experiment.py` | `fdf412b89e7d0cadde17975f1209b61d59addf2f860aca2e77c20ca5d45430d3` | `fdf412b89e7d0cadde17975f1209b61d59addf2f860aca2e77c20ca5d45430d3` | idêntico |
| `src/silent_voice/vision/swinlip_embedding_dataset.py` | `17b638919b30470f5c3e03c871111c3ed8baf9665decd35f775d0133b5aaf631` | `17b638919b30470f5c3e03c871111c3ed8baf9665decd35f775d0133b5aaf631` | idêntico |
| `src/silent_voice/vision/swinlip_frozen_encoder.py` | `d47e7e76368bc64d3863a10ddbe346dbc042d55292a329cda957968b54943e23` | `d47e7e76368bc64d3863a10ddbe346dbc042d55292a329cda957968b54943e23` | idêntico |
| `src/silent_voice/vision/swinlip_frozen_loso.py` | `494a97784f406e1148d648761b2b537d30792f034267744d66e14dc1a6db9fb5` | `494a97784f406e1148d648761b2b537d30792f034267744d66e14dc1a6db9fb5` | idêntico |
| `src/silent_voice/vision/swinlip_frozen_probe.py` | `aa048142a64aef7aa85189e4cb94bcbc4cccc3f562aa0e3b750587eb6481a0dc` | `aa048142a64aef7aa85189e4cb94bcbc4cccc3f562aa0e3b750587eb6481a0dc` | idêntico |
| `src/silent_voice/vision/temporal_features.py` | `7127246a6f6083a33c77d09d6a533679f9575f8710354fe26459b4ed7ab17435` | `7127246a6f6083a33c77d09d6a533679f9575f8710354fe26459b4ed7ab17435` | idêntico |
| `src/silent_voice/vision/video_sequence.py` | `0ad1c1469661b2580acb1f68adcd865e14b8b463bfa0bf788e5041c161e76020` | `0ad1c1469661b2580acb1f68adcd865e14b8b463bfa0bf788e5041c161e76020` | idêntico |
| `src/silent_voice/vision/visual_activity_segmentation.py` | `68cb90e356a96a5bb13e7f1379d237eaefb1cfb8190ac4459fb9541579e32c4f` | `68cb90e356a96a5bb13e7f1379d237eaefb1cfb8190ac4459fb9541579e32c4f` | idêntico |
| `src/silent_voice/vision/visual_cross_validation.py` | `45e5462adb19e57a53c793be1d3a66e4bfe136b6427b800f8a70a241b8618c17` | `45e5462adb19e57a53c793be1d3a66e4bfe136b6427b800f8a70a241b8618c17` | idêntico |
| `src/silent_voice/vision/visual_dataset_processing.py` | `d8cea3b7898c76b59b95f184881549b7c14e9c28819fafb639ec6b9373ecaee5` | `d8cea3b7898c76b59b95f184881549b7c14e9c28819fafb639ec6b9373ecaee5` | idêntico |
| `src/silent_voice/vision/visual_experiment_defaults.py` | `39474b0fed1a1930ef966323327990821ffbadd3804a23f593925f25bb683740` | `39474b0fed1a1930ef966323327990821ffbadd3804a23f593925f25bb683740` | idêntico |
| `src/silent_voice/vision/visual_personalization_candidates.py` | `c09a568096b49483807cbb0acce5b6a2a76cf6099ca8f74f4508307f2095b5fb` | `c09a568096b49483807cbb0acce5b6a2a76cf6099ca8f74f4508307f2095b5fb` | idêntico |
| `src/silent_voice/vision/visual_personalization_feature_build.py` | `4a86120f701e28feb756a6f102c713bcb369f69fab6681035f5e44b1a81369b1` | `2cf02a04bac431670bd34fa0b7b1ac62e2eb86ce9a397df878411112e8ff8b74` | derivado |
| `src/silent_voice/vision/visual_sample_processing.py` | `c9011d9a41e42059a2246441d5f28f8081c0b4c43bd6f425cee6f6396646ae14` | `c9011d9a41e42059a2246441d5f28f8081c0b4c43bd6f425cee6f6396646ae14` | idêntico |
| `src/silent_voice/vision/visual_sample_segmentation.py` | `b355430643887068f38d9fd65bc84a14955c15d693f51c74799bbe4f11692bec` | `b355430643887068f38d9fd65bc84a14955c15d693f51c74799bbe4f11692bec` | idêntico |
| `src/silent_voice/vision/visual_sequence_resampling.py` | `fc8c3650dbb1ec74dd6b076f4554964b5b8eda7f8279d7b682449b0a7654f516` | `fc8c3650dbb1ec74dd6b076f4554964b5b8eda7f8279d7b682449b0a7654f516` | idêntico |
| `src/silent_voice/vision/visual_training_dataset.py` | `f2fde8b2a822d14e56156a9edec631f0e6acd93b3a84cd577d80ac3b8743a01c` | `f2fde8b2a822d14e56156a9edec631f0e6acd93b3a84cd577d80ac3b8743a01c` | idêntico |
| `tests/test_public_personalization_contract.py` | `novo` | `046e21c24f89e5d57c991886601ea97c42e0518145f34085ee81673244643f9c` | novo |
| `tests/unit/inference/test_global_live_visual_tester.py` | `47eb7407e96dda4ab6ca677e976a3a7324e459932c9a3f33cf7ab144a65176a2` | `3d5efcd5cb6aaa39d2433c58cbb01e3568c7523162b9830f1156936933341bba` | derivado |
| `tests/unit/inference/test_live_context_session.py` | `906c2db38bd94070aa8d88a74141a179a33044822ee215021da5d28f002b1608` | `906c2db38bd94070aa8d88a74141a179a33044822ee215021da5d28f002b1608` | idêntico |
| `tests/unit/inference/test_live_visual_tester.py` | `3e5dc01b33ab68b90fbeac0fcad34075955e2dccace016d2d4f9005e5cc02313` | `3e5dc01b33ab68b90fbeac0fcad34075955e2dccace016d2d4f9005e5cc02313` | idêntico |
| `tests/unit/inference/test_personal_live_visual_tester.py` | `dd30519ccce8ea9baaea3b5c06781959b6030b431032d6ae5cefc48c30313c31` | `893623dd15c3bc48e31fed8ac4f5463f37b20415aaec91e090ff49995ebeb599` | derivado |
| `tests/unit/test_c44_reproducibility.py` | `d93d619cb6326ba71656c07f08e9bddd9875514617a02b1ed3b8be005fd7c52b` | `0e43fc3c484d1b6f74a0499f6ae07e80739e79132651d74c0b085a58e3ac2f94` | derivado |

Este documento é novo e não inclui seu próprio hash; deve ser calculado após sua criação. A lista não autoriza adicionar outros arquivos.

## Preservação dos bytes na migração

As regras explícitas em `.gitattributes` correspondem aos 111 arquivos públicos e preservam seus bytes de trabalho em materializações com `core.autocrlf=true` e `false`. Para documentos congelados e arquivos com fins de linha mistos, `-text` preserva os bytes; para os demais, `text eol=lf` ou `text eol=crlf` corresponde à representação registrada. Os hashes científicos e conteúdos dos documentos congelados permanecem intactos.

| Arquivo adicional em ai | SHA-256 |
| --- | --- |
| `requirements-live-tester-win-cp312.lock` | `f68bbe4c7a69f1d1160afc93d51e3eae7d64853f8b7091820e3bd85759fcb38c` |
| `docs/python_reproducibility.md` | `d2a5f19949d93dc9dc6edc1dac3ec1310b96f1f4a4ce85cd5cc6c76f0a9ff5d6` |

O hash deste manifesto é calculado separadamente após a atualização. O teste de materialização isolado verifica os 111 arquivos, incluindo este manifesto.
