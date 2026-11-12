// Default IELTS Vocabulary Database
const DEFAULT_VOCAB_LIST = [
  // 1. Environment & Climate
  {
    id: 1,
    word: "biodiversity",
    phonetic: "/ˌbaɪ.əʊ.daɪˈvɜː.sə.ti/",
    pos: "noun",
    vietnamese: "Đa dạng sinh học",
    english: "The variety of plant and animal life in a particular habitat.",
    collocation: "preserve / conserve biodiversity",
    example: "Deforestation poses a direct threat to the rich biodiversity of tropical rainforests.",
    topic: "Environment",
    band: "7.0+"
  },
  {
    id: 2,
    word: "mitigate",
    phonetic: "/ˈmɪt.ɪ.ɡeɪt/",
    pos: "verb",
    vietnamese: "Giảm nhẹ, làm dịu bớt (hậu quả, tác động)",
    english: "To make something less harmful, unpleasant, or bad.",
    collocation: "mitigate the effects / impact of climate change",
    example: "Governments must implement strict regulations to mitigate the environmental damage caused by heavy industries.",
    topic: "Environment",
    band: "7.5+"
  },
  {
    id: 3,
    word: "unsustainable",
    phonetic: "/ˌʌn.səˈsteɪ.nə.bəl/",
    pos: "adj",
    vietnamese: "Không bền vững, không thể duy trì lâu dài",
    english: "Not able to be maintained at the current rate or level without causing depletion.",
    collocation: "unsustainable consumption / depletion of resources",
    example: "The current reliance on fossil fuels is ecologically and economically unsustainable.",
    topic: "Environment",
    band: "7.0+"
  },
  {
    id: 4,
    word: "degradation",
    phonetic: "/ˌdeɡ.rəˈdeɪ.ʃən/",
    pos: "noun",
    vietnamese: "Sự suy thoái, xuống cấp",
    english: "The process in which the quality of something is destroyed or spoiled.",
    collocation: "environmental / soil degradation",
    example: "Overgrazing and illegal logging lead to severe land degradation in rural regions.",
    topic: "Environment",
    band: "7.5+"
  },
  {
    id: 5,
    word: "renewable",
    phonetic: "/rɪˈnjuː.ə.bəl/",
    pos: "adj",
    vietnamese: "Có thể tái tạo, tái sinh",
    english: "Natural energy resources that are not depleted by use.",
    collocation: "renewable energy sources / transition to renewables",
    example: "Investing heavily in renewable energy is crucial for achieving carbon neutrality by 2050.",
    topic: "Environment",
    band: "6.5+"
  },

  // 2. Technology & AI
  {
    id: 6,
    word: "ubiquitous",
    phonetic: "/juːˈbɪk.wɪ.təs/",
    pos: "adj",
    vietnamese: "Phổ biến ở khắp mọi nơi",
    english: "Present, appearing, or found everywhere at the same time.",
    collocation: "become ubiquitous / ubiquitous presence of smartphones",
    example: "Mobile devices and AI algorithms have become ubiquitous in modern everyday life.",
    topic: "Technology",
    band: "8.0+"
  },
  {
    id: 7,
    word: "autonomous",
    phonetic: "/ɔːˈtɒn.ə.məs/",
    pos: "adj",
    vietnamese: "Tự hành, tự trị, độc lập",
    english: "Acting independently or having the freedom to do so without external control.",
    collocation: "autonomous vehicles / autonomous learning",
    example: "The advent of autonomous vehicles is poised to revolutionize the logistics and transportation sector.",
    topic: "Technology",
    band: "7.5+"
  },
  {
    id: 8,
    word: "revolutionize",
    phonetic: "/ˌrev.əˈluː.ʃən.aɪz/",
    pos: "verb",
    vietnamese: "Cách mạng hóa, thay đổi hoàn toàn",
    english: "To completely change the way something is done, made, or thought about.",
    collocation: "revolutionize the way people communicate",
    example: "Artificial intelligence continues to revolutionize medical diagnostics and disease prevention.",
    topic: "Technology",
    band: "7.0+"
  },
  {
    id: 9,
    word: "obsolete",
    phonetic: "/ˌɒb.səˈliːt/",
    pos: "adj",
    vietnamese: "Lỗi thời, không còn sử dụng",
    english: "No longer in use or out of date because something newer has replaced it.",
    collocation: "render sth obsolete / technically obsolete",
    example: "Rapid technological progress can quickly render previous hardware obsolete within a few years.",
    topic: "Technology",
    band: "7.5+"
  },
  {
    id: 10,
    word: "cutting-edge",
    phonetic: "/ˌkʌt.ɪŋ ˈedʒ/",
    pos: "adj",
    vietnamese: "Tiên tiến nhất, hiện đại nhất",
    english: "Highly advanced, innovative, and pioneering.",
    collocation: "cutting-edge technology / research",
    example: "The university invested millions in cutting-edge laboratory equipment to attract top global researchers.",
    topic: "Technology",
    band: "7.0+"
  },

  // 3. Education & Learning
  {
    id: 11,
    word: "pedagogical",
    phonetic: "/ˌped.əˈɡɒdʒ.ɪ.kəl/",
    pos: "adj",
    vietnamese: "Thuộc về sư phạm, phương pháp giảng dạy",
    english: "Relating to the methods and theory of teaching.",
    collocation: "pedagogical approaches / methods / skills",
    example: "Modern educators place emphasis on interactive pedagogical approaches rather than passive rote memorization.",
    topic: "Education",
    band: "8.0+"
  },
  {
    id: 12,
    word: "holistic",
    phonetic: "/həʊˈlɪs.tɪk/",
    pos: "adj",
    vietnamese: "Toàn diện, tổng thể",
    english: "Dealing with or treating the whole of something or someone and not just a part.",
    collocation: "holistic development / a holistic approach to education",
    example: "Schools should foster a holistic environment that nurtures both academic prowess and emotional resilience.",
    topic: "Education",
    band: "7.5+"
  },
  {
    id: 13,
    word: "foster",
    phonetic: "/ˈfɒs.tər/",
    pos: "verb",
    vietnamese: "Nuôi dưỡng, bồi đắp, khuyến khích phát triển",
    english: "To encourage or promote the development or growth of ideas or feelings.",
    collocation: "foster creativity / innovation / a sense of community",
    example: "Collaborative classroom activities foster essential teamwork and problem-solving skills among students.",
    topic: "Education",
    band: "7.0+"
  },

  // 4. Work & Economy
  {
    id: 14,
    word: "lucrative",
    phonetic: "/ˈluː.krə.tɪv/",
    pos: "adj",
    vietnamese: "Sinh lợi cao, mang lại nhiều tiền",
    english: "Producing a great deal of profit or wealth.",
    collocation: "a lucrative career / business venture / market",
    example: "Software engineering remains one of the most lucrative career paths for young graduates today.",
    topic: "Economy",
    band: "7.5+"
  },
  {
    id: 15,
    word: "precarious",
    phonetic: "/prɪˈkeə.ri.əs/",
    pos: "adj",
    vietnamese: "Bấp bênh, nguy hiểm, không chắc chắn",
    english: "Not securely held or in position; dangerously likely to fall or collapse; uncertain.",
    collocation: "precarious employment / financial position",
    example: "Gig economy workers frequently endure precarious working conditions with minimal social benefits.",
    topic: "Economy",
    band: "8.0+"
  },

  // 5. Health & Psychology
  {
    id: 16,
    word: "sedentary",
    phonetic: "/ˈsed.ən.tər.i/",
    pos: "adj",
    vietnamese: "Ít vận động, ngồi nhiều một chỗ",
    english: "Involving little exercise or physical activity and spending much time seated.",
    collocation: "a sedentary lifestyle / sedentary desk job",
    example: "Leading a sedentary lifestyle is widely recognized as a principal risk factor for cardiovascular disease.",
    topic: "Health",
    band: "7.0+"
  },
  {
    id: 17,
    word: "detrimental",
    phonetic: "/ˌdet.rɪˈmen.təl/",
    pos: "adj",
    vietnamese: "Có hại, gây bất lợi",
    english: "Causing harm, damage, or disadvantage.",
    collocation: "have a detrimental effect / impact on health",
    example: "Excessive consumption of ultra-processed food exerts detrimental effects on metabolic well-being.",
    topic: "Health",
    band: "7.5+"
  },
  {
    id: 18,
    word: "resilience",
    phonetic: "/rɪˈzɪl.jəns/",
    pos: "noun",
    vietnamese: "Khả năng phục hồi, sự kiên cường",
    english: "The capacity to recover quickly from difficulties; toughness.",
    collocation: "psychological resilience / build resilience",
    example: "Practicing mindfulness regularly can help individuals cultivate psychological resilience against chronic stress.",
    topic: "Health",
    band: "7.5+"
  },

  // 6. Society & Urbanization
  {
    id: 19,
    word: "sprawling",
    phonetic: "/ˈsprɔː.lɪŋ/",
    pos: "adj",
    vietnamese: "Trải dài, lan rộng (đô thị)",
    english: "Spreading out over a large area in an untidy or irregular way.",
    collocation: "sprawling metropolis / urban sprawl",
    example: "Efficient rapid transit systems are imperative to connect sprawling suburban communities with the city center.",
    topic: "Society",
    band: "7.5+"
  },
  {
    id: 20,
    word: "cosmopolitan",
    phonetic: "/ˌkɒz.məˈpɒl.ɪ.tən/",
    pos: "adj",
    vietnamese: "Mang tính quốc tế, đa văn hóa",
    english: "Containing people and things from many different parts of the world.",
    collocation: "a cosmopolitan city / atmosphere",
    example: "London and New York are renowned for their vibrant and cosmopolitan demographic landscapes.",
    topic: "Society",
    band: "7.5+"
  }
];

if (typeof window !== "undefined") {
  window.DEFAULT_VOCAB_LIST = DEFAULT_VOCAB_LIST;
}

