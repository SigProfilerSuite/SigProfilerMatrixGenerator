import ftplib
import hashlib
import tarfile
import subprocess
import os
import shutil
import logging
import time

from pathlib import Path
from SigProfilerMatrixGenerator.scripts import ref_install

# Constants
FTP_SERVERS = {
    "alexandrovlab": {
        "address": "alexandrovlab-ftp.ucsd.edu",
        "path": "pub/tools/SigProfilerMatrixGenerator/",
    },
    "sanger": {
        "address": "ngs.sanger.ac.uk",
        "path": "scratch/project/mutographs/SigProf/",
    },
}
CHECKSUMS = {
    "GRCh37": {
        "1": "a7d51305e943cf06ff2029146bd91bca",
        "2": "d24d0185af89356d44614ab0d6fd6a68",
        "3": "ea5e033147dcaf77bfd4c70f50688d37",
        "4": "00d7797c7184f1802367e33f6e2bc3da",
        "5": "f74b1eeb329088242a9f22a16322b325",
        "6": "b353cc4c4abc90340e7747509fe7b457",
        "7": "bbadde91b3ef958c7d20e2b1088c8cd2",
        "8": "0ff695692e3efebaf00c7905d0d536d7",
        "9": "40b75a18acb66748a37888c53a76dcdb",
        "10": "557881b744a932b4ceee8a06d6de85a4",
        "11": "f8b8f118101d7cb04164b29a7acadca4",
        "12": "52c18e9fefc3ed3e35c1d8771d1247de",
        "13": "a241d1cdcadccfd94db792300ab000bf",
        "14": "ed3907128336795669bc19d77c0aa409",
        "15": "bfc66ad087c4e9025076d7571cffa30e",
        "16": "bd251fddc42400bb54ef95d5e1002ece",
        "17": "fcd36b1bf5c4bd74328dc4caaae244ae",
        "18": "e015d4324c36374827582c5b1214a736",
        "19": "5cfa7d47e2d73dbdbf8d68f97c8e8b23",
        "20": "2fa0717bf4e8dddac64cd393f4134ff5",
        "21": "ba5559776d4601b80ca42c82f02102a4",
        "22": "ba762b6ae493df40d04d1ff63d9b2933",
        "Y": "0303100be91874b966a998273cd7c8eb",
        "X": "14e331d82736f6cfc177ff8c90f7bd78",
        "MT": "dfd6db5743d399516d5c8dadee5bee78",
    },
    "GRCh37_havana": {
        "1": "a954558ed4a92c33454f8539d5e47d43",
        "2": "f2a1702c668d531656ffbeadb5bb1b66",
        "3": "e6a4d10c433d8707a1a336e310a779bc",
        "4": "709d6d8ab80b8f83f2f8892e23a9adba",
        "5": "fa4fe82dce241cf4eeaf84ef9b44030f",
        "6": "161d68063347fff0fe5d82a1c60cdef4",
        "7": "5f866a10820d3d48d3b96fb8432ade8e",
        "8": "585c7100d1de569df883910bbf01463c",
        "9": "5667fc1a44a93b6f162bf60d4f6a21c1",
        "10": "7684e3198ac4c484b56d6e91b8f2fc15",
        "11": "e3b5501a11be7d5fcf9219933467c86a",
        "12": "511a8b89d19e47df4633da5f277373b5",
        "13": "7b621f0c18db0592c0f82db9b760ceef",
        "14": "16b383fa1dbf30feb8a5d1d89a9ac7af",
        "15": "f3295833a4dfd7a628ca9befe1972739",
        "16": "9985d8cf725dcd29b3ded0a4eeb426e2",
        "17": "9118e1200b7cd95a4d5c95ff0e039c7c",
        "18": "116ae0ba70ea43b10983ddd07387d6dd",
        "19": "930c568fe249b78a602a3400ce094b83",
        "20": "fa24f27c160dffd5d8b7c6270dff4a0d",
        "21": "4f6f61d43c698e2c66dc62f21f7ad6cd",
        "22": "77661703e7b65ad2b6adcb75e7e3e53b",
        "Y": "b86042fd443490fb0061478037392fc0",
        "X": "02b7328d7d74704d571fd38149bbf814",
    },
    "GRCh38": {
        "1": "ebe083105e7703a49581a36d73732a96",
        "2": "cd65e36dbdf12a8ac3d2c70ebac8cad4",
        "3": "6c20a7008394f2fa9c304d231a1f391b",
        "4": "5c7443e1678868adadeac0e57558f6e8",
        "5": "45573232c8097c679503a6598f61e60b",
        "6": "cfc137c7434d3a9a872332d405b5c553",
        "7": "9d8210c22c1962db837e7b62a578975c",
        "8": "665134fd44f21915cbeef955addf89ba",
        "9": "758d0c0c71d8bafbe1ede86587191730",
        "10": "397bb21acff1ca3052ac802f2aee06e0",
        "11": "07707ff8a2a964656469a7be7bb3e576",
        "12": "506d02539075e080ee12ebdf63908080",
        "13": "03ed22f01ab43145733c0b6a647e0560",
        "14": "8b93447086549e476c65699ed813a567",
        "15": "cd0dfe9fa78cae2fc7becf8f8ec6c693",
        "16": "e17bbb66eb4d6b62b7b0e2fbf062b6a6",
        "17": "8fc95bb3101d024d890aa3543eb454c5",
        "18": "a4870628045bb033a90e8c89f818e24d",
        "19": "6a9d0c8298f0ba2fa13180e02b969f16",
        "20": "aa75d35969cf3956bb4ace7bdc57b34e",
        "21": "5d55f5ad6271d6a0d8806876924990f7",
        "22": "efdb4e1d23ab7964302b828062a33447",
        "Y": "3b38c639ad164d60f1a055b46fcd2748",
        "X": "d5edbea3cf5d1716765dd4a7b41b7656",
        "MT": "dfd6db5743d399516d5c8dadee5bee78",
    },
    "CHM13-T2T": {
        "1": "8160d885ea68cbd9e1a85f1a62f5c0f1",
        "2": "5041bd8918b488102bd3fc17f4eff66e",
        "3": "b499fea5aea8934cb8de2531157d49ec",
        "4": "a2a3a52de2cca0e9fb5781901e1dfba8",
        "5": "ee7f9612de6e8b1ec484c02b2b31e9fe",
        "6": "2f9202597543ae1adc1dd31571a9c3d2",
        "7": "be89f4bcc4553389fcc4e5f225db77da",
        "8": "b0934433605dca7314235cc4059de0bb",
        "9": "c669a1e483304201a6afa38ea0cedc53",
        "10": "272a6ea1ec1bbbc3d5f34bd59df76457",
        "11": "7bfa1f75f0c08c7ae7ff660f3171c6a6",
        "12": "5fb792acd7f9cb00b1cc707b28d13723",
        "13": "40cc90706b67aca49d409ef158e00685",
        "14": "1a10df3d0fb9206d93fc3791666a54ae",
        "15": "c60b41404acf203ffff4251c95ccb94c",
        "16": "130a73687af01742dd35b0b5fbc225bb",
        "17": "3b0ad5efe98372b5bf3e18d5938098de",
        "18": "df7f62810c54fa7aa2d0c20481344252",
        "19": "1e9f2c8bb1f11e45c1789a3e69c03094",
        "20": "548df0167cbd6401d5f5b1c1050f7065",
        "21": "460c01106a2402a25591a625c6a8ff73",
        "22": "8d3aa47b4456add9d0b78cb70b155fda",
        "X": "13dea22db0695374c214c15211c65424",
        "Y": "2323d989382a60e2e4a2e60c7cd4c9a4",
    },
    "GRCh38_havana": {
        "1": "c4ef4ee14a4f0f7b319e9ed01f2a9742",
        "2": "189cb33da673afcf161b7724d78d314b",
        "3": "19fb72b2f4bebca66969d9eaaab0b06b",
        "4": "04069627d35462add3095cd14299c181",
        "5": "e3fbab13e69a5ba48c9bf706215aef19",
        "6": "7de52b0136f65c25b2f3652e8888449a",
        "7": "0071cc7e4024b0d81941df353ce99fdc",
        "8": "c19f322ee6a786e94e665b1ab3f459ea",
        "9": "00920f091df48d3dba8b270432bb38a8",
        "10": "dfcdfcc0a2524888e91f9a40aa2289e5",
        "11": "01118568e33f876f31f4d0585085b844",
        "12": "11b6ffc45b5d198344e8d0f2e51fa08a",
        "13": "e1241284e80f9a3afe204131c9eb6192",
        "14": "b8d68bd919dc87483679314d0dae9514",
        "15": "ca2c6d19dadc4d905013b37dfaa75fa6",
        "16": "ccf7fe495c7ff7c11c430a935050bb4d",
        "17": "ec09c6c67cc0496117da52bc584cab8f",
        "18": "e8edcd9275c659101745570b0ddc436d",
        "19": "293befa3316b6bb8b5a2a2c75e5e8030",
        "20": "4065b4403e1b9659f9f049c4c886ed7f",
        "21": "3f661bcfd29bf7153b4bfb95e8d112d8",
        "22": "ea31a6d2cdac7d8aeb2e3be0688b4159",
        "Y": "a68939c10c3ebc16340785bf99366328",
        "X": "57623734b88f441f5499955d2c83a6f9",
    },
    "mm9": {
        "1": "c5afc4b3f7f2119696214511d7a04341",
        "2": "a7b467475a1b032d2c893dac1c419a28",
        "3": "f922bc529a17324f1cd858f9a8723d65",
        "4": "f3d6b74e3c04dbd229e2f1e363607506",
        "5": "5fee4f1889c9fe20f7f8562c62bbeb0a",
        "6": "481d47b87da45f3a20181c780fd796c2",
        "7": "454ef2bf49a5ba8cfea3d16dfcfc7f25",
        "8": "2f4162d4c824db78a2a2a820cb4fec81",
        "9": "0649e6aec61af1ab8ab4797ea8e54119",
        "10": "38296256bcfe886c8ae771418e4fd824",
        "11": "b31cb0ce693e35eaa77031d44b12e474",
        "12": "d2b3e4b015742b6aea30ceec5a972968",
        "13": "df77b6d0ed1b133224b128c189736372",
        "14": "0ec3c0e6b3fa2cdb957541f19792e130",
        "15": "44fcaf2ec9b82dae910f85ce41c3cfad",
        "16": "ad7a8dbdf46fa7077e0982a54eab70b7",
        "17": "71aee1dee3cd2078e4619c485d88817e",
        "18": "727ec4ed3128ecacd6cd2f7558083553",
        "19": "461a7119781ab7f4b654fdd9ef76e0ec",
        "Y": "471ff3bbb4520c020cfaa7ca8371c543",
        "X": "9ccadf96cd3aa0ed9d299894a3d7fde0",
        "MT": "a1d56043ed8308908965dd080a4d0c8d",
    },
    "mm10": {
        "1": "ef88c5ac276a32a2865c0408f92acd55",
        "2": "ced7325ef9e2dfedea3fbe26428a6059",
        "3": "9cd1794eeea27553077a018038303908",
        "4": "da616d7ed6c67f824487eb2ed09cd33b",
        "5": "b327b82da6986bf947105d07c0ad6d2e",
        "6": "fb9a8fa0b85561f8d4de633c22d5157a",
        "7": "12457fd80f6806779fc0d4cc8d36fbad",
        "8": "5d98d86bd22bee1cb226406f49ee7caf",
        "9": "b2f26613fcc622a4003e4c945ae55e25",
        "10": "e9f3589529e258ede66d2e77bb87d21d",
        "11": "76bcd285c3c66471ad6fccfabe42294c",
        "12": "ac34fc3616c9609d8e75a59069e9007a",
        "13": "f81b976e4e4617b25945d06f9aa30846",
        "14": "95dc042eb2aa7d4cc0abe071d4d7966e",
        "15": "fbf2477833aff73ae085537cd7ee0f85",
        "16": "77cbcd009ba50891571f785595717ec1",
        "17": "cd9e4dfdd168ed3de05dac4d44c6e692",
        "18": "945e83694c7c8f69d6186e1a2abc9771",
        "19": "e57b25f8869de31a9dbce06510711db6",
        "Y": "c2146ba4ab1ec262f5e38b2a1ebc5f5b",
        "X": "9af543088be046fdc63976c2d41de94c",
        "MT": "a1d56043ed8308908965dd080a4d0c8d",
    },
    "mm39": {
        "1": "57c0e2508c3f8fe66a792be344f494d9",
        "2": "8e69643ce8f9ff048eae0113f64ce8b7",
        "3": "0a1f33496316ecc245868ca72dc4ac95",
        "4": "15f59279c79b0b23cda1cac00aec9b2f",
        "5": "cd6709c54421184266eea49be266378c",
        "6": "916484773b14295b4711e9f13efd1c94",
        "7": "04a6a77f0754a0b6badd825c0e8729ff",
        "8": "2f68f81e848940f3e8e5e4e2e9f5c6bc",
        "9": "f2cefa27e8d26e588d32212c78c5b840",
        "10": "5f877fd57657884cdc3c09036a365314",
        "11": "1b7b5162cc876b2fb0502e010daf1a50",
        "12": "cfccf49fc2034eebd66ea40e2410c482",
        "13": "a411479e72e6ee2fc9b1667a7598de0d",
        "14": "11dfe2f88d544c1402be18bc732a7b80",
        "15": "9d71bd08f73fe51d24856c804cb86b38",
        "16": "9b97d374745941c370e35596846e2738",
        "17": "4a698fcd2e16eea7d7a718c94747e85d",
        "18": "fe0a2d35beb0407114a9e61b6ed646f2",
        "19": "c51fa76818b0447e13047095251796eb",
        "Y": "554d0a9f1062fb12903e521c866e2600",
        "X": "ce0f276bc6eab955c22a0111bc436ad7",
    },
    "mm10_havana": {
        "1": "8351fa274b2e49b159fdfd1a17b8e522",
        "2": "afa7459e3fa1a40f96279d318e3f6fc4",
        "3": "106064694826ed8b9cfd29c5cfe39f1d",
        "4": "807aafbf65a28995b2ff64c040f54ff8",
        "5": "afc3c4640788db5b8866d7644be4c49d",
        "6": "2eff5f397f61735e90dc4089705751bc",
        "7": "f62fe7d720c219bacbe91fb0624fdb33",
        "8": "1e523de22029fc4feea1e3222638d3ec",
        "9": "3b75a1f2360ef49cbdc3da16a1e40d23",
        "10": "2d3cbd3aa1b5f6c78a11bc799787d226",
        "11": "9b5e62ac65c2e05e7c09d7b3ac9aa507",
        "12": "07e2bfe001933efb9052458f203fd8d4",
        "13": "4df084dfa4d2ea80519da4fa825d7c6e",
        "14": "c4c01a321c2e8b67ed619dc91588d1cc",
        "15": "6ccda29f891ac9d17567c69a1b47a40a",
        "16": "7df7554d6b3d7ca8331fe163e4930a64",
        "17": "60ecd93b145f36226c246356701422f2",
        "18": "b52767b6bbc3a293993652e78db7ddac",
        "19": "5a246e5963dc0a300765b5cdd87e07d9",
        "Y": "da73d749cd65735db5fd10556ae2376a",
        "X": "ab9c1ad518e71b15ff543cda415a463f",
    },
    "rn6": {
        "1": "003723513cbdb3708fcc5d737c05199c",
        "2": "53e52c5facc7f05462be533845f37425",
        "3": "8d157a9b71fe9770cf783ea5459b19d7",
        "4": "a66dc1999bcc960ff11fe0b24c0d7b14",
        "5": "601cf83411234adbdd9f911b89509564",
        "6": "03b1f4af58fffdf213466ea85b570b3d",
        "7": "4ed05ddf9502ef79e121c02e391660e6",
        "8": "3e2458daaf1b3e8ab4d0e0a9e60c067b",
        "9": "8f83caeccec7ea6e35e404737138ee67",
        "10": "9c1af453a5facc9bfa821457bcfc4d30",
        "11": "ef0480a905c55d76a3c58e295a85bc75",
        "12": "643b6fe4a3a6363ffe64a6c316fa3e1a",
        "13": "102bb3fb420a4104c216bcdf99870374",
        "14": "e26b8b63fba0ea7ced4f0330e93a8cdc",
        "15": "da747616a1362d374d4786102fab6f9f",
        "16": "54e4f932eb0eda4cbf31156f96ef7235",
        "17": "46c2facf5415e4eff8b0804161db722d",
        "18": "f1cb84f002967854b83bf266ec59a7a3",
        "19": "b85ca155fd1780fe5c327a4589c212a6",
        "20": "1f7efe08722aa6a87e49b23e8e1a94c2",
        "Y": "6a7a3539c329dc540dfa6db006003bb1",
        "X": "7a06bafab97c59a819f03633f0a6b7a2",
        "MT": "cb841662629aa1b6c1b7b0b3a8f689d1",
    },
    "rn7": {
        "1": "9c9a4ee818dd0baac1035486df990409",
        "2": "771b58630048ebc9476663dcffdc7700",
        "3": "f98c53989fa3b54d2a695b964512df74",
        "4": "10b8e45b1ea161b16e8875c337bcae28",
        "5": "73967db06384d090d178de8c48eba4b0",
        "6": "b1a7dc1957a49fd0393cccc74cfdf76e",
        "7": "3b00439a7d5f862e9c290c525f9341ec",
        "8": "4ad00baadc094c9acbe4ef61489db0f2",
        "9": "308e363133ffe6d1c4776790844d338c",
        "10": "d9a6d6e9f03b3ecbf0950846e11e918e",
        "11": "4168e50dce4c12424a8128f7ee2973f5",
        "12": "bbfcf9de3a3ff22a7e648635d7445024",
        "13": "591babc89e7d35c367a081dc3855e4d9",
        "14": "4e32573f0bf39fc4c8390921e0e246e9",
        "15": "b6fd1919fd8f1f2a52898c333b21e7f5",
        "16": "00d8b8ac66ba0ee6fc25ac1be4c72bec",
        "17": "911e574cc631b6fa6e3602fc2cb0cb59",
        "18": "43302f483e17ab90392eecf7cb99d0af",
        "19": "4674a2fb5665b849007f9236a2046fdf",
        "20": "ce629500eb98a5bb9b61e58c7afad319",
        "Y": "4e7b96a995965c8991b979c54d2084d4",
        "X": "da58cb6ea3490508ce494df6d895e923",
        "MT": "e23feef31e91545a122a4d305f982d5c",
    },
    "c_elegans": {
        "I": "5a3ea8cf3dfbc641716b7bc805edcaae",
        "II": "bf82edaa92809dd2fea2b791c38c9728",
        "III": "d2df34b6743f41d3964549fc76c5f1a2",
        "IV": "23396bb57145d3acde2888947b5b8c3a",
        "V": "09df3c53b12e5fd7d9035cc98ca221a3",
        "X": "988046456f1409dfdb5e26444d84d238",
        "MtDNA": "48983f530959780de0125f74a87d4fc1",
    },
    "dog": {
        "1": "bef8283c1a36f9aef0e407de2ff6af00",
        "2": "9cc961192bb5e58b3847060c3e9c1cfc",
        "3": "d33263fa2de6666b41e140cb7a8da66c",
        "4": "cd4ed39ebac1c04800ccf30466ec69f5",
        "5": "c0f48a4a764e58388b48835aca2ec0a4",
        "6": "4b472a2f8d0a53ac75cce04e7dc9279a",
        "7": "12a61573a0da2c9306fff705bb1c39c1",
        "8": "e22cf22a27560aa8523dc959ddcf6e25",
        "9": "c079a73d719145cdd5c7c93969a1c392",
        "10": "45805a518147f7846bd0457ca038c8df",
        "11": "f38cda8508463a7607dff14a581ee7b0",
        "12": "adb5de197f58bb827fa01fe924eb3a1d",
        "13": "055a845ba97baad3b13d4d3359f88290",
        "14": "27f0ba8e47996a058807a3827cf8e4a8",
        "15": "2e9565c687a593eb0acbdd0962bb9255",
        "16": "89b2225bb78d88b0fd1d38d9514ab0cb",
        "17": "f0378253e2f083e42b665ea202fde3b0",
        "18": "04d124e273f3b54a685ad6526223cd03",
        "19": "67bae093919e6bb5ab6b9806c739d539",
        "20": "5588387165a2e19c4533012cfb4998f3",
        "21": "371cdf18a545728f7964b9db2fc72d5e",
        "22": "fbf76865f88a018d93506e036f6a68bc",
        "23": "085145e01d9fd9f0f999fb9e8e8d4400",
        "24": "69b75a9962fb766b447e7d1252cb31ac",
        "25": "12d5c6677b3e17170c317c1f5532d2a8",
        "26": "13937d18e56b2b93d12fa5fcba48a138",
        "27": "1d03d8ca5f201f4d156f5e1b38f7a67c",
        "28": "c33395dec7fdc13e9d8f10afaa946f8c",
        "29": "174f2db104ecaa5efef770f44241e3b0",
        "30": "047d420ef9aecb933a7d83b6af820b23",
        "31": "5be61f0c9944a5f2d7d1a5b2e75fb000",
        "32": "212dcb867e95a642277a243fed8d8e41",
        "33": "08a217b02cdd778cfdb0005dff4828b1",
        "34": "4245d6fc370d9049ef4c25314fbef239",
        "35": "1344aba8755b8a4e304629180fc0591a",
        "36": "e4fff6ed84777905dc999ca6d6bc2557",
        "37": "60d51ea6ae9e3f2fa316e3d03aff96b2",
        "38": "4090ff76d94e6b38920916ae3ff2441c",
        "X": "bce1372df64037d79b0995311d8ff971",
    },
    "ebv": {"gi_82503188_ref_NC_007605": "7f8894e52b0cac1f968c0402838bea07"},
    "yeast": {
        "I": "49fe0862d533d1c6ad66d534216e8ab9",
        "II": "d8f6151b5cc080601fd759267f674fba",
        "III": "4c80933f7958261369d68ed84bfa8d5f",
        "IV": "afdb839d9289c33cea42f3bc53f978b1",
        "V": "48e5530f587b97fcfbc4742261ded994",
        "VI": "0cc51e4f21f3d3f89b98061428002f95",
        "VII": "c9566b7a2264909ea0cee9202ef93e55",
        "VIII": "66193457ece167d15330dc3be2fbb0ef",
        "IX": "b3f57177000e0322c824ffdab69cb7ed",
        "X": "ad715c5261132608d27e79d8e8bc68a7",
        "XI": "5d84fe013b962aafade20413bb82758a",
        "XII": "740b5b5dc0dd3f30bc67d391b15bf639",
        "XIII": "87691656b7200080f728f990d4f74877",
        "XIV": "270346a6575023f7bc9e7f4f8e750fd1",
        "XV": "89ee60c9779424d666268508df34bad9",
        "XVI": "3d72cbd3bc4bb1bff109e5ecea70fd2d",
        "M": "64b4f865366c9cee76635019f30712c0",
    },
}

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")


class GenomeDownloadError(RuntimeError):
    """Raised when a reference genome archive cannot be downloaded or installed."""


class ReferenceGenomeManager:
    """
    A class for downloading and managing reference genomes.
    """

    def __init__(self, reference_dir=None):
        self.reference_dir = ref_install.reference_dir(
            secondary_chromosome_install_dir=reference_dir
        )

    def download_genome(self, genome_name):
        """
        Downloads the specified genome from the FTP server and installs it in the reference directory.
        """
        if self.is_genome_installed(genome_name):
            logging.info(f"{genome_name} is already installed.")
            return

        logging.info(f"Downloading {genome_name}...")

        file_name = f"{genome_name}.tar.gz"
        local_filepath = self.reference_dir.get_tsb_dir() / file_name
        local_filepath.parent.mkdir(parents=True, exist_ok=True)

        downloaded = False
        failures = []

        # First try to download using FTP
        for server_key in FTP_SERVERS:
            server_info = FTP_SERVERS[server_key]
            try:
                self._remove_partial_archive(local_filepath)
                self._download_via_ftplib(
                    server_info["address"],
                    server_info["path"],
                    file_name,
                    local_filepath,
                )
                if self._downloaded_archive_exists(local_filepath):
                    logging.info(
                        f"Downloaded {genome_name} from {server_key} using FTP."
                    )
                    downloaded = True
                    break  # Exit the loop if download is successful
                failures.append(
                    f"{server_key} FTP: download completed but did not create "
                    f"{local_filepath}."
                )
            except ftplib.all_errors as e:
                failures.append(f"{server_key} FTP: {e}")
                logging.info(f"Attempt to download from {server_key} failed: {e}")
            if downloaded:
                break
            if shutil.which("curl"):
                try:
                    self._remove_partial_archive(local_filepath)
                    self._download_via_curl(
                        server_info["address"],
                        server_info["path"],
                        file_name,
                        local_filepath,
                    )
                    if self._downloaded_archive_exists(local_filepath):
                        logging.info(f"Downloaded {genome_name} using curl.")
                        downloaded = True
                        break  # Exit the loop if download is successful
                    failures.append(
                        f"{server_key} curl: download completed but did not create "
                        f"{local_filepath}."
                    )
                except (subprocess.CalledProcessError, OSError) as e:
                    failures.append(f"{server_key} curl: {e}")
                    logging.error(f"Curl download failed with error: {e}")
            else:
                failures.append(f"{server_key} curl: curl is not available.")
                logging.error("Curl is not available. Unable to download the file.")

        if not downloaded:
            self._remove_partial_archive(local_filepath)
            raise GenomeDownloadError(
                self._format_download_failure_message(file_name, failures)
            )

        try:
            self._unzip_file(local_filepath)
        except (tarfile.TarError, OSError) as e:
            self._remove_partial_archive(local_filepath)
            raise GenomeDownloadError(
                f"Downloaded archive {local_filepath} could not be extracted. "
                "Please retry the installation; if the problem persists, manually "
                "download a fresh archive and install it with --local_genome in the "
                "CLI or offline_files_path in the Python API."
            ) from e
        local_filepath.unlink()
        logging.info(f"{genome_name} has been successfully installed.")

    def install_local_genome(self, genome_name, local_genome_dir):
        """
        Install a reference genome originating from the FTP server that is stored locally.

        - genome_name (str): The name of the genome.
        - local_genome_dir (Path or str): The local directory path where the genome archive is stored.
        """

        local_genome_dir = Path(local_genome_dir)
        archive_file_path = local_genome_dir / f"{genome_name}.tar.gz"

        # Verify that the local genome file exists
        if not archive_file_path.exists():
            logging.error(f"Local genome file {archive_file_path} does not exist.")
            return

        # Extract the archive
        try:
            self._unzip_file(archive_file_path)
        except tarfile.TarError as e:
            logging.error(f"Error extracting the archive: {e}")
            return

        # Verify that all necessary files are extracted and have correct checksums
        if not self.is_genome_installed(genome_name):
            logging.error(f"Installation verification failed for {genome_name}.")
            self.print_genome_checksum_verification_report(genome_name)
            return

        logging.info(
            f"{genome_name} has been successfully installed from the local file."
        )

    def is_genome_installed(self, genome_name):
        """
        Verifies whether all files for specified genome is fully and correctly installed.

        Parameters:
        - genome_name (str): The name of the genome to check.

        Returns:
        - bool: True if all files for the genome are present and have the correct checksums, False otherwise.
        """
        if genome_name not in CHECKSUMS:
            return False
        for file, checksum in CHECKSUMS[genome_name].items():
            file_with_extension = f"{file}.txt"
            file_path = (
                self.reference_dir.get_tsb_dir() / genome_name / file_with_extension
            )

            if not file_path.exists() or not self._verify_checksum(file_path, checksum):
                return False
        return True

    def print_available_genomes_report(self):
        """
        Prints a table of all available genomes and their installation status.
        """
        genome_status = self._list_all_genomes_with_installation_status()

        # Determine the maximum length of genome names for formatting
        max_genome_name_length = max(len(genome) for genome in genome_status.keys())

        # Print the header of the table
        header = f"{'Genome':<{max_genome_name_length}}    Available"
        print(header)
        print("-" * len(header))

        # Sort the genomes alphabetically and iterate over them
        for genome in sorted(genome_status.keys()):
            status = genome_status[genome]
            availability = "Yes" if status == "Installed" else "No"
            print(f"{genome:<{max_genome_name_length}}    {availability}")

    def print_genome_checksum_verification_report(self, genome_name):
        """
        Prints a table of all files for the specified genome and their checksum verification status.
        """
        if genome_name not in CHECKSUMS:
            logging.error(f"No checksum information available for {genome_name}.")
            return

        file_checksums = CHECKSUMS[genome_name]
        max_file_name_length = max(len(file) for file in file_checksums.keys()) + 4

        header = f"{'File':<{max_file_name_length}} | {'Status':<8} | {'Expected MD5':<32} | {'Actual MD5':<32}"
        print(header)
        print("-" * len(header))

        for file, expected_md5 in file_checksums.items():
            file_with_extension = f"{file}.txt"
            file_path = (
                self.reference_dir.get_tsb_dir() / genome_name / file_with_extension
            )

            if file_path.exists():
                actual_md5 = self._calculate_md5(file_path)
                status = "Match" if expected_md5 == actual_md5 else "Mismatch"
            else:
                actual_md5 = "N/A"
                status = "Missing"

            print(
                f"{file_with_extension:<{max_file_name_length}} | {status:<8} | {expected_md5:<32} | {actual_md5:<32}"
            )

    def _download_via_ftplib(self, ftp_server, ftp_path, filename, local_filepath):
        def download_progress(block):
            nonlocal total_downloaded, start_time, last_reported_progress
            total_downloaded += len(block)

            # Calculate the download progress and speed
            elapsed_time = time.time() - start_time
            if elapsed_time > 0:
                speed = (
                    total_downloaded / elapsed_time / 1024 / 1024
                )  # Convert bytes per second to megabytes per second
                speed_str = f"{speed:.2f} MB/s"  # Format speed as MB/s
            else:
                speed_str = "Calculating..."

            # Format the amount downloaded and total file size
            downloaded_str = (
                f"{total_downloaded/1024/1024:.2f} MB of {file_size/1024/1024:.2f} MB"
            )

            # Calculate and format the download percentage
            progress = total_downloaded / file_size * 100

            # Update the progress bar if the change is at least 1%
            if progress - last_reported_progress >= 1 or progress == 100:
                print(
                    f"\rDownloading: {progress:.2f}% [{downloaded_str}] at {speed_str}",
                    end="",
                )
                last_reported_progress = progress  # Update the last reported progress

            f.write(block)  # Write the received block to the file

        os.makedirs(local_filepath.parent, exist_ok=True)
        with ftplib.FTP(ftp_server) as ftp:
            ftp.login()
            ftp.cwd(ftp_path)

            # Retrieve the size of the file
            ftp.sendcmd("TYPE I")  # Switch to Binary mode
            file_size = ftp.size(filename)
            total_downloaded = 0
            start_time = time.time()  # Record the start time of the download
            last_reported_progress = -1  # Initialize the last reported progress

            with open(local_filepath, "wb") as f:
                # Use the callback function to display progress and write to the file
                ftp.retrbinary("RETR " + filename, download_progress, 1024)
            print("\nDownload complete.")

    def _download_via_curl(self, ftp_server, ftp_path, filename, local_filepath):
        """
        Download a file from FTP server using curl.
        Helper function for download_genome.
        """
        try:
            local_filepath.parent.mkdir(parents=True, exist_ok=True)
            url = f"ftp://{ftp_server}/{ftp_path.rstrip('/')}/{filename}"
            command = [
                "curl",
                "--fail",
                "--location",
                "--retry",
                "3",
                "--connect-timeout",
                "30",
                "-o",
                str(local_filepath),
                url,
            ]
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Curl download failed with error: {e}.")
            raise

    def _downloaded_archive_exists(self, local_filepath):
        return local_filepath.exists() and local_filepath.stat().st_size > 0

    def _remove_partial_archive(self, local_filepath):
        try:
            local_filepath.unlink()
        except FileNotFoundError:
            pass

    def _format_download_failure_message(self, file_name, failures):
        message = [
            f"Unable to download {file_name} from the configured reference genome mirrors.",
        ]
        if failures:
            message.append("Download attempts failed with:")
            message.extend(f"  - {failure}" for failure in failures)
        message.append(
            "Please check FTP/network access or manually download the archive from "
            "ftp://alexandrovlab-ftp.ucsd.edu/pub/tools/SigProfilerMatrixGenerator/ "
            "and install it with --local_genome in the CLI or offline_files_path in "
            "the Python API. Both options expect the directory containing the archive."
        )
        return "\n".join(message)

    def _unzip_file(self, file_path):
        with tarfile.open(file_path, "r:gz") as tar:
            extraction_options = {}
            if hasattr(tarfile, "data_filter"):
                extraction_options["filter"] = "data"
            tar.extractall(
                path=self.reference_dir.get_tsb_dir(), **extraction_options
            )

    def _verify_checksum(self, file_path, checksum):
        """
        Returns True if the checksum matches, False otherwise.
        """
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest() == checksum

    def _list_all_genomes_with_installation_status(self):
        genome_status = {}
        for genome in CHECKSUMS.keys():
            genome_status[genome] = (
                "Installed" if self.is_genome_installed(genome) else "Not Installed"
            )
        return genome_status

    def _calculate_md5(self, file_path):
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
