def quiz(q, answers, correct, img="", t=20):
    return {"type": "quiz", "q": q, "qk": "", "img": img, "a": answers, "ak": ["", "", "", ""][: len(answers)], "c": correct, "t": t, "p": 500}


def tf(q, correct, img="", t=15):
    return {"type": "truefalse", "q": q, "qk": "", "img": img, "a": ["True", "False"], "ak": ["ពិត", "មិនពិត"], "c": 0 if correct else 1, "t": t, "p": 500}


def typed(q, accepted, img="", t=25):
    return {"type": "type", "q": q, "qk": "", "img": img, "a": [], "ak": [], "c": 0, "acc": accepted, "t": t, "p": 500}


def order(q, items, img="", t=30):
    return {"type": "order", "q": q, "qk": "", "img": img, "a": [], "ak": [], "c": 0, "items": items, "t": t, "p": 500}


def slider(q, lo, hi, ans, tol=0, step=1, img="", t=20):
    return {"type": "slider", "q": q, "qk": "", "img": img, "a": [], "ak": [], "c": 0, "min": lo, "max": hi, "step": step, "ans": ans, "tol": tol, "t": t, "p": 500}


def match(q, pairs, img="", t=35):
    return {"type": "match", "q": q, "qk": "", "img": img, "a": [], "ak": [], "c": 0, "pairs": pairs, "t": t, "p": 500}


def memory(q, cards, img="", t=45):
    return {"type": "memory", "q": q, "qk": "", "img": img, "a": [], "ak": [], "c": 0, "cards": cards, "t": t, "p": 500}


TEMPLATE_DATA = [
    {
        "emoji": "❓", "name": "Animal quiz", "desc": "Pick the right animal answer", "tag": "Live-ready", "color": "#ffd9a8", "type": "quiz", "skin": "jungle", "subject": "Science", "age": "4–6",
        "questions": [
            quiz("Which animal says moo?", ["Cow", "Dog", "Duck", "Pig"], 0, "🐮"),
            quiz("Which animal has a long trunk?", ["Lion", "Elephant", "Frog", "Owl"], 1, "🐘"),
            quiz("Which animal can fly?", ["Fish", "Dog", "Bird", "Cow"], 2, "🐦"),
            quiz("Which animal hops and says ribbit?", ["Frog", "Horse", "Bear", "Cat"], 0, "🐸"),
            quiz("Which animal is black and white and eats bamboo?", ["Panda", "Fox", "Rabbit", "Lion"], 0, "🐼"),
        ],
    },
    {
        "emoji": "🎨", "name": "Color quiz", "desc": "Name the colour of things", "tag": "Young kids", "color": "#ffc9de", "type": "quiz", "skin": "candy", "subject": "Colors", "age": "3–5",
        "questions": [
            quiz("What color is a banana?", ["Red", "Blue", "Yellow", "Green"], 2, "🍌", 15),
            quiz("What color is grass?", ["Purple", "Green", "Orange", "White"], 1, "🌿", 15),
            quiz("What color is a strawberry?", ["Red", "Blue", "Green", "Gray"], 0, "🍓", 15),
            quiz("What color is a carrot?", ["Pink", "Orange", "Blue", "Black"], 1, "🥕", 15),
            quiz("What color is the sky on a sunny day?", ["Blue", "Pink", "Black", "Brown"], 0, "☀️", 15),
        ],
    },
    {
        "emoji": "🚀", "name": "Space quiz", "desc": "Explore planets and stars", "tag": "Solo", "color": "#dcd3ff", "type": "quiz", "skin": "space", "subject": "Science", "age": "6–8",
        "questions": [
            quiz("Which planet do we live on?", ["Mars", "Earth", "Venus", "Jupiter"], 1, "🌍"),
            quiz("What shines in the sky at night?", ["The Moon", "A rainbow", "A cloud", "A bird"], 0, "🌙"),
            quiz("Which is the biggest planet?", ["Mercury", "Earth", "Jupiter", "Mars"], 2, "🪐"),
            quiz("What gives us light in the day?", ["The Sun", "The Moon", "A star", "A lamp"], 0, "☀️"),
            quiz("What do astronauts ride into space?", ["A boat", "A rocket", "A bus", "A bike"], 1, "🚀"),
        ],
    },
    {
        "emoji": "🏯", "name": "Cambodia quiz", "desc": "Learn about Cambodia", "tag": "Languages", "color": "#c9f2a8", "type": "quiz", "skin": "desert", "subject": "Culture", "age": "6–9",
        "questions": [
            quiz("What is the capital of Cambodia?", ["Siem Reap", "Phnom Penh", "Battambang", "Kampot"], 1, "🏙️"),
            quiz("Which famous temple is in Siem Reap?", ["Angkor Wat", "Eiffel Tower", "Big Ben", "Taj Mahal"], 0, "🏯"),
            quiz("Which river flows through Phnom Penh?", ["Mekong", "Nile", "Amazon", "Thames"], 0, "🌊"),
            quiz("What is the Khmer New Year season called?", ["Choul Chnam Thmey", "Pchum Ben", "Water Festival", "Christmas"], 0, "🎉"),
            quiz("Which animal is a symbol of Cambodia?", ["Elephant", "Penguin", "Kangaroo", "Polar bear"], 0, "🐘"),
        ],
    },
    {
        "emoji": "🔢", "name": "Maths quiz", "desc": "Add and subtract with choices", "tag": "Math", "color": "#ffe3a3", "type": "quiz", "skin": "space", "subject": "Math", "age": "5–8",
        "questions": [
            quiz("What is 2 + 3?", ["4", "5", "6", "7"], 1, "➕", 15),
            quiz("What is 5 − 2?", ["1", "2", "3", "4"], 2, "➖", 15),
            quiz("What is 4 + 4?", ["6", "7", "8", "9"], 2, "🔢", 15),
            quiz("What is 10 − 6?", ["3", "4", "5", "6"], 1, "➖", 15),
            quiz("What is 3 + 7?", ["9", "10", "11", "12"], 1, "➕", 15),
        ],
    },
    {
        "emoji": "🍎", "name": "Fruit quiz", "desc": "Tasty questions about fruit", "tag": "Young kids", "color": "#ffd0d0", "type": "quiz", "skin": "farm", "subject": "Food", "age": "3–6",
        "questions": [
            quiz("Which fruit is yellow and curved?", ["Apple", "Banana", "Grape", "Mango"], 1, "🍌"),
            quiz("Which fruit is red and round?", ["Apple", "Lemon", "Kiwi", "Pear"], 0, "🍎"),
            quiz("Which fruit has hard shell and sweet water?", ["Coconut", "Orange", "Plum", "Fig"], 0, "🥥"),
            quiz("Which fruit is called the king of fruits in Cambodia?", ["Durian", "Apple", "Peach", "Cherry"], 0, "🍈"),
        ],
    },
    {
        "emoji": "✅", "name": "True / False", "desc": "Is it right or wrong?", "tag": "Live-ready", "color": "#c9f2a8", "type": "truefalse", "skin": "ocean", "subject": "Science", "age": "5–8",
        "questions": [
            tf("A whale is a fish.", False, "🐋"),
            tf("The sun rises in the east.", True, "🌅"),
            tf("Spiders have eight legs.", True, "🕷️"),
            tf("Penguins can fly.", False, "🐧"),
            tf("Water freezes into ice when it is very cold.", True, "🧊"),
        ],
    },
    {
        "emoji": "🧼", "name": "Healthy habits", "desc": "True or false about staying healthy", "tag": "Young kids", "color": "#d9f0e0", "type": "truefalse", "skin": "jungle", "subject": "Health", "age": "4–7",
        "questions": [
            tf("We should wash our hands before eating.", True, "🧼"),
            tf("Candy is the best breakfast every day.", False, "🍬"),
            tf("We should brush our teeth twice a day.", True, "🪥"),
            tf("Sleeping helps our body grow.", True, "😴"),
            tf("Vegetables are bad for you.", False, "🥦"),
        ],
    },
    {
        "emoji": "✍️", "name": "Fill the blank", "desc": "Type the missing word", "tag": "Live-ready", "color": "#c7e8ff", "type": "type", "skin": "candy", "subject": "Language", "age": "6–9",
        "questions": [
            typed("A baby cat is called a ____.", ["kitten"], "🐱"),
            typed("The opposite of hot is ____.", ["cold"], "🥶"),
            typed("A ____ gives us milk.", ["cow"], "🐮"),
            typed("We use our eyes to ____.", ["see", "look"], "👀"),
            typed("Two plus two equals ____ (word).", ["four", "4"], "➕"),
        ],
    },
    {
        "emoji": "🔤", "name": "Spelling", "desc": "Spell the word you see", "tag": "Solo", "color": "#ffd0d0", "type": "type", "skin": "farm", "subject": "Language", "age": "5–8",
        "questions": [
            typed("Spell this animal", ["dog"], "🐶"),
            typed("Spell this fruit", ["apple"], "🍎"),
            typed("Spell this vehicle", ["car"], "🚗"),
            typed("Spell this object", ["book"], "📖"),
            typed("Spell this plant", ["tree"], "🌳"),
        ],
    },
    {
        "emoji": "🔢", "name": "Sequencing", "desc": "Put the steps in order", "tag": "Solo", "color": "#e6d6ff", "type": "order", "skin": "space", "subject": "Logic", "age": "5–8",
        "questions": [
            order("Put the days in order", ["Monday", "Tuesday", "Wednesday", "Thursday"], "📅"),
            order("Put the numbers in order", ["1", "2", "3", "4", "5"], "🔢"),
            order("How does a butterfly grow?", ["Egg", "Caterpillar", "Chrysalis", "Butterfly"], "🦋"),
            order("Brush your teeth", ["Wet the brush", "Add toothpaste", "Brush gently", "Rinse your mouth"], "🪥"),
        ],
    },
    {
        "emoji": "🌱", "name": "Plant life cycle", "desc": "Order how things grow", "tag": "Solo", "color": "#d4f5c4", "type": "order", "skin": "jungle", "subject": "Science", "age": "6–9",
        "questions": [
            order("How does a plant grow?", ["Seed", "Sprout", "Small plant", "Flower"], "🌱"),
            order("Put the day in order", ["Wake up", "Eat breakfast", "Go to school", "Go to bed"], "🌞"),
            order("Order from smallest to biggest", ["Ant", "Cat", "Horse", "Elephant"], "🐘"),
        ],
    },
    {
        "emoji": "🎯", "name": "Guess the number", "desc": "Slide to the right number", "tag": "Math", "color": "#ffd9a8", "type": "slider", "skin": "desert", "subject": "Math", "age": "5–9",
        "questions": [
            slider("How many days are in a week?", 0, 14, 7, 0, 1, "📅"),
            slider("How many fingers on two hands?", 0, 20, 10, 0, 1, "🖐️"),
            slider("How many legs does a spider have?", 0, 12, 8, 0, 1, "🕷️"),
            slider("How many months in a year?", 0, 24, 12, 0, 1, "🗓️"),
            slider("About how many minutes in an hour?", 0, 120, 60, 5, 5, "⏰"),
        ],
    },
    {
        "emoji": "🔟", "name": "Counting", "desc": "Count and slide the answer", "tag": "Young kids", "color": "#ffd9a8", "type": "slider", "skin": "farm", "subject": "Math", "age": "3–6",
        "questions": [
            slider("How many ducks? 🦆🦆🦆", 0, 10, 3, 0, 1, "🦆"),
            slider("How many stars? ⭐⭐⭐⭐⭐", 0, 10, 5, 0, 1, "⭐"),
            slider("How many hearts? ❤️❤️❤️❤️", 0, 10, 4, 0, 1, "❤️"),
            slider("How many apples? 🍎🍎", 0, 10, 2, 0, 1, "🍎"),
        ],
    },
    {
        "emoji": "🔗", "name": "Matching", "desc": "Connect the pairs", "tag": "Solo", "color": "#dcd3ff", "type": "match", "skin": "candy", "subject": "General", "age": "5–8",
        "questions": [
            match("Match the animal to its home", [["🐝", "Hive"], ["🐦", "Nest"], ["🐟", "Water"], ["🐻", "Cave"]], "🏠"),
            match("Match the fruit to its color", [["🍌", "Yellow"], ["🍓", "Red"], ["🍏", "Green"], ["🍇", "Purple"]], "🍎"),
            match("Match the baby to its parent", [["Puppy", "Dog"], ["Kitten", "Cat"], ["Chick", "Hen"], ["Calf", "Cow"]], "👶"),
        ],
    },
    {
        "emoji": "🔡", "name": "Letters & words", "desc": "Match letters to pictures", "tag": "Languages", "color": "#ffc9de", "type": "match", "skin": "ocean", "subject": "Letters", "age": "4–7",
        "questions": [
            match("Match the letter to the animal", [["A", "🐜"], ["B", "🐻"], ["C", "🐱"], ["D", "🐶"]], "🔤"),
            match("Match the number to the dots", [["1", "●"], ["2", "●●"], ["3", "●●●"], ["4", "●●●●"]], "🔢"),
        ],
    },
    {
        "emoji": "🃏", "name": "Memory match", "desc": "Flip cards to find pairs", "tag": "Young kids", "color": "#bdf1e6", "type": "memory", "skin": "farm", "subject": "Memory", "age": "3–7",
        "questions": [
            memory("Find the farm friends", ["🐮", "🐷", "🐔"]),
            memory("Find the pairs", ["🐑", "🐴", "🦆", "🐰"]),
            memory("Find all the pairs", ["🐮", "🐷", "🐔", "🐑", "🐴", "🦆"], "", 60),
        ],
    },
    {
        "emoji": "🍓", "name": "Fruit memory", "desc": "Match the fruit cards", "tag": "Young kids", "color": "#ffd0d0", "type": "memory", "skin": "candy", "subject": "Memory", "age": "3–7",
        "questions": [
            memory("Find the fruits", ["🍎", "🍌", "🍇"]),
            memory("Find the pairs", ["🍓", "🍊", "🍉", "🍍"]),
        ],
    },
    {
        "emoji": "🏆", "name": "Mixed challenge", "desc": "Every question type in one game", "tag": "Live-ready", "color": "#ffe0b8", "type": "mixed", "skin": "space", "subject": "General", "age": "6–9",
        "questions": [
            quiz("Which planet do we live on?", ["Mars", "Earth", "Venus", "Jupiter"], 1, "🌍"),
            tf("Spiders have eight legs.", True, "🕷️"),
            typed("A baby cat is called a ____.", ["kitten"], "🐱"),
            order("How does a butterfly grow?", ["Egg", "Caterpillar", "Chrysalis", "Butterfly"], "🦋"),
            slider("How many days are in a week?", 0, 14, 7, 0, 1, "📅"),
            match("Match the fruit to its color", [["🍌", "Yellow"], ["🍓", "Red"], ["🍏", "Green"]], "🍎"),
            memory("Find the pairs", ["🐮", "🐷", "🐔"]),
        ],
    },
    {
        "emoji": "📝", "name": "Blank game", "desc": "Start empty and build it yourself", "tag": "Solo", "color": "#f0e8ff", "type": "quiz", "skin": "jungle", "subject": "General", "age": "4–8",
        "questions": [quiz("Type your first question", ["Answer 1", "Answer 2", "Answer 3", "Answer 4"], 0, "❓")],
    },
]


def lesson(title, text, img="📖", t=15):
    return {"type": "lesson", "q": title, "qk": "", "text": text, "textk": "", "img": img, "a": [], "ak": [], "c": 0, "t": t, "p": 0}


TEMPLATE_DATA += [
    {
        "emoji": "🏷️", "name": "Grammar: nouns", "desc": "Learn naming words, then practise", "tag": "Languages", "color": "#c7e8ff", "type": "mixed", "skin": "sky", "subject": "Grammar", "age": "6–8",
        "settings": {"dark": False, "track": "calm"},
        "questions": [
            lesson("What is a noun?", "A noun is a naming word. It names a person, an animal, a place or a thing. Cat, teacher, school and ball are all nouns.", "🏷️", 20),
            quiz("Which word is a noun?", ["run", "happy", "dog", "quickly"], 2, "🐶"),
            quiz("Which word is a noun?", ["table", "jump", "blue", "slowly"], 0, "🪑"),
            tf("The word 'school' is a noun.", True, "🏫"),
            typed("Type a noun for this picture", ["cat", "kitten"], "🐱"),
        ],
    },
    {
        "emoji": "🏃", "name": "Grammar: verbs", "desc": "Action words made easy", "tag": "Languages", "color": "#ffd9a8", "type": "mixed", "skin": "sunny", "subject": "Grammar", "age": "6–8",
        "settings": {"dark": False},
        "questions": [
            lesson("What is a verb?", "A verb is an action word. It tells us what someone does. Run, jump, eat and sing are verbs.", "🏃", 20),
            quiz("Which word is a verb?", ["table", "jump", "green", "tall"], 1, "🤸"),
            quiz("Which word is a verb?", ["sing", "flower", "red", "tiny"], 0, "🎤"),
            tf("The word 'eat' is an action word.", True, "🍎"),
            typed("Type an action word for this picture", ["swim", "swimming"], "🏊"),
        ],
    },
    {
        "emoji": "🅰️", "name": "A or An", "desc": "Choose the right little word", "tag": "Languages", "color": "#ffc9de", "type": "mixed", "skin": "candy", "subject": "Grammar", "age": "5–7",
        "settings": {"dark": False},
        "questions": [
            lesson("A or An?", "We use 'an' before the vowel sounds a, e, i, o, u. We use 'a' before the other letters. An apple. A banana.", "🅰️", 18),
            quiz("___ apple", ["a", "an"], 1, "🍎"),
            quiz("___ dog", ["a", "an"], 0, "🐶"),
            quiz("___ egg", ["a", "an"], 1, "🥚"),
            quiz("___ cat", ["a", "an"], 0, "🐱"),
        ],
    },
    {
        "emoji": "↔️", "name": "Opposites", "desc": "Match words with their opposites", "tag": "Languages", "color": "#dcd3ff", "type": "mixed", "skin": "grape", "subject": "Vocabulary", "age": "4–7",
        "questions": [
            match("Match the opposites", [["Hot", "Cold"], ["Big", "Small"], ["Up", "Down"], ["Happy", "Sad"]], "↔️"),
            quiz("The opposite of 'day' is…", ["Night", "Sun", "Morning", "Light"], 0, "🌙"),
            quiz("The opposite of 'open' is…", ["Close", "Push", "Door", "Look"], 0, "🚪"),
            typed("The opposite of 'fast' is ____.", ["slow"], "🐢"),
        ],
    },
    {
        "emoji": "📚", "name": "Plurals", "desc": "One or many? Type the plural", "tag": "Languages", "color": "#d4f5c4", "type": "type", "skin": "mint", "subject": "Grammar", "age": "6–8",
        "settings": {"dark": False},
        "questions": [
            lesson("Plurals", "Plural means more than one. Most words add -s: one cat, two cats. Some change: one child, two children.", "📚", 20),
            typed("One dog, two ____", ["dogs"], "🐶🐶"),
            typed("One book, two ____", ["books"], "📖📖"),
            typed("One child, two ____", ["children"], "🧒🧒"),
            typed("One mouse, two ____", ["mice"], "🐭🐭"),
        ],
    },
    {
        "emoji": "🎵", "name": "Rhyming words", "desc": "Find the words that sound alike", "tag": "Languages", "color": "#ffe3a3", "type": "mixed", "skin": "gold", "subject": "Phonics", "age": "4–7",
        "settings": {"dark": False, "track": "party"},
        "questions": [
            match("Match the rhymes", [["Cat", "Hat"], ["Dog", "Frog"], ["Sun", "Fun"], ["Bee", "Tree"]], "🎵"),
            quiz("Which word rhymes with 'cake'?", ["Lake", "Dog", "Sun", "Tree"], 0, "🍰"),
            quiz("Which word rhymes with 'star'?", ["Car", "Moon", "Sky", "Day"], 0, "⭐"),
        ],
    },
    {
        "emoji": "🔡", "name": "Phonics: first sound", "desc": "Which letter does it start with?", "tag": "Young kids", "color": "#ffd0d0", "type": "quiz", "skin": "coral", "subject": "Phonics", "age": "3–6",
        "settings": {"dark": False},
        "questions": [
            quiz("What letter does this start with?", ["B", "D", "P", "T"], 0, "🐻"),
            quiz("What letter does this start with?", ["C", "S", "K", "M"], 0, "🐱"),
            quiz("What letter does this start with?", ["F", "H", "G", "J"], 0, "🐸"),
            quiz("What letter does this start with?", ["M", "N", "L", "W"], 0, "🐵"),
            quiz("What letter does this start with?", ["S", "Z", "C", "X"], 0, "☀️"),
        ],
    },
    {
        "emoji": "📅", "name": "Days & months", "desc": "Learn the calendar in order", "tag": "Solo", "color": "#e6d6ff", "type": "order", "skin": "grape", "subject": "Time", "age": "5–8",
        "questions": [
            lesson("Days of the week", "There are seven days in a week: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday and Sunday.", "📅", 18),
            order("Put the weekdays in order", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], "📅"),
            order("Put the seasons in order", ["Spring", "Summer", "Autumn", "Winter"], "🍂"),
            order("Put the first months in order", ["January", "February", "March", "April"], "🗓️"),
        ],
    },
    {
        "emoji": "ក", "name": "Khmer letters", "desc": "Say the sound of each Khmer letter", "tag": "Languages", "color": "#ffc9de", "type": "quiz", "skin": "coral", "subject": "Khmer", "age": "5–8",
        "settings": {"dark": False},
        "questions": [
            quiz("Which sound does this letter make?", ["ka", "kha", "ko", "ngo"], 0, "ក", 15),
            quiz("Which sound does this letter make?", ["kha", "ka", "cha", "cho"], 0, "ខ", 15),
            quiz("Which sound does this letter make?", ["ko", "kho", "ka", "ngo"], 0, "គ", 15),
            quiz("Which sound does this letter make?", ["ngo", "ko", "cha", "nho"], 0, "ង", 15),
            quiz("Which sound does this letter make?", ["cha", "chha", "cho", "ka"], 0, "ច", 15),
        ],
    },
    {
        "emoji": "🔷", "name": "Shapes", "desc": "Name the shapes around us", "tag": "Young kids", "color": "#ffe3a3", "type": "quiz", "skin": "gold", "subject": "Shapes", "age": "3–6",
        "settings": {"dark": False},
        "questions": [
            quiz("What shape is this?", ["Circle", "Square", "Triangle", "Star"], 0, "🔴"),
            quiz("What shape is this?", ["Square", "Circle", "Heart", "Moon"], 0, "🟦"),
            quiz("What shape is this?", ["Triangle", "Square", "Circle", "Diamond"], 0, "🔺"),
            quiz("What shape is this?", ["Heart", "Star", "Moon", "Circle"], 0, "❤️"),
            quiz("What shape is this?", ["Star", "Heart", "Circle", "Square"], 0, "⭐"),
        ],
    },
    {
        "emoji": "🎤", "name": "Sing & learn", "desc": "A calm lesson with soft music", "tag": "Young kids", "color": "#d9f0e0", "type": "mixed", "skin": "meadow", "subject": "Music", "age": "3–6",
        "settings": {"dark": False, "track": "calm"},
        "questions": [
            lesson("The ABC song", "A B C D E F G. H I J K L M N O P. Q R S, T U V. W X Y and Z. Now I know my ABCs!", "🎵", 20),
            quiz("What letter comes after A?", ["B", "C", "D", "Z"], 0, "🔤"),
            quiz("What letter comes after C?", ["D", "B", "F", "A"], 0, "🔤"),
            order("Put the letters in order", ["A", "B", "C", "D"], "🔤"),
        ],
    },
]


def obj(oid, kind, text, x, y, w, h, role="decor", fs=6, color="", target=""):
    return {"id": oid, "kind": kind, "text": text, "x": x, "y": y, "w": w, "h": h, "fs": fs, "color": color, "role": role, "target": target}


def scene(title, mode, objs, bg="", t=30):
    return {"type": "canvas", "q": title, "qk": "", "img": "", "a": [], "ak": [], "c": 0, "t": t, "p": 500, "mode": mode, "bg": bg, "objs": objs}


TEMPLATE_DATA += [
    {
        "emoji": "🎯", "name": "Tap the animals", "desc": "Custom scene: tap every animal you find", "tag": "Young kids", "color": "#ffd9a8", "type": "canvas", "skin": "meadow", "subject": "Animals", "age": "3–6",
        "settings": {"dark": False},
        "questions": [
            scene("Tap all the animals!", "tap", [
                obj("a1", "emoji", "🐶", 8, 18, 16, 22, "correct", 11),
                obj("a2", "emoji", "🐱", 40, 8, 16, 22, "correct", 11),
                obj("a3", "emoji", "🚗", 70, 20, 16, 22, "wrong", 11),
                obj("a4", "emoji", "🐰", 20, 58, 16, 22, "correct", 11),
                obj("a5", "emoji", "🍎", 55, 60, 16, 22, "wrong", 11),
                obj("a6", "emoji", "🐸", 78, 62, 16, 22, "correct", 11),
            ], "linear-gradient(180deg,#bfe9ff,#d8f5c8)", 25),
            scene("Tap only the fruit!", "tap", [
                obj("b1", "emoji", "🍎", 10, 20, 16, 22, "correct", 11),
                obj("b2", "emoji", "🐻", 42, 10, 16, 22, "wrong", 11),
                obj("b3", "emoji", "🍌", 72, 22, 16, 22, "correct", 11),
                obj("b4", "emoji", "🚲", 25, 60, 16, 22, "wrong", 11),
                obj("b5", "emoji", "🍇", 60, 60, 16, 22, "correct", 11),
            ], "linear-gradient(180deg,#fff2bf,#ffd9a8)", 25),
        ],
    },
    {
        "emoji": "🏠", "name": "Drag to the home", "desc": "Custom scene: drag each animal to its home", "tag": "Young kids", "color": "#bdf1e6", "type": "canvas", "skin": "mint", "subject": "Animals", "age": "4–7",
        "settings": {"dark": False},
        "questions": [
            scene("Drag each animal to its home!", "drag", [
                obj("z1", "zone", "Water", 4, 58, 28, 34, "target", 3.2, "#7cc7ff"),
                obj("z2", "zone", "Tree", 36, 58, 28, 34, "target", 3.2, "#8fe08a"),
                obj("z3", "zone", "Barn", 68, 58, 28, 34, "target", 3.2, "#ffc27a"),
                obj("d1", "emoji", "🐟", 8, 8, 16, 22, "drag", 11, "", "z1"),
                obj("d2", "emoji", "🐦", 42, 8, 16, 22, "drag", 11, "", "z2"),
                obj("d3", "emoji", "🐮", 74, 8, 16, 22, "drag", 11, "", "z3"),
            ], "linear-gradient(180deg,#e6f7ff,#f4ffe6)", 40),
            scene("Put the food on the right plate!", "drag", [
                obj("y1", "zone", "Fruit", 6, 58, 40, 34, "target", 3.2, "#ffb3c6"),
                obj("y2", "zone", "Vegetable", 54, 58, 40, 34, "target", 3.2, "#b8e986"),
                obj("e1", "emoji", "🍎", 8, 8, 16, 22, "drag", 11, "", "y1"),
                obj("e2", "emoji", "🥕", 32, 8, 16, 22, "drag", 11, "", "y2"),
                obj("e3", "emoji", "🍌", 56, 8, 16, 22, "drag", 11, "", "y1"),
                obj("e4", "emoji", "🥦", 78, 8, 16, 22, "drag", 11, "", "y2"),
            ], "linear-gradient(180deg,#fff7e6,#ffe9d6)", 40),
        ],
    },
]
