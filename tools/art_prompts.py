"""Curated paintings for every scene of studio/scenelib.py. The planner only picks the scene; the picture itself is never invented by
a weak model. One clear literal subject per prompt; variants keep reels different. M / W / K = the recurring Uzbek figures."""
M = "Uzbek man in white skullcap and dark blue coat seen from behind"
W = "woman in long hijab seen from behind"
K = "little boy in white skullcap seen from behind"

ART = {
    "father_son": [f"{M} holding hands with {K}, walking along an orchard path", f"{M} and {K} sitting side by side on a wooden bench in a courtyard under a grape vine",
                   f"{M} crouching beside {K} at the edge of a green field"],
    "advice_repeat": [f"{M} standing and talking to {K} in a clay-walled courtyard", f"{M} and {K} standing face to the sunset on a hill, the man's arm raised, pointing"],
    "not_listening": [f"{K} running away after a red ball across a courtyard, {M} left standing behind", f"{K} sitting alone turned away in the corner of a courtyard, a red ball beside him"],
    "family_meal": ["low round table with round flatbread, teapot, tea bowls, grapes and plov on a red carpet", "big dish of plov, pomegranates and flatbread on an embroidered tablecloth",
                    f"family seen from behind sitting around a low table with teapot and bread in a courtyard"],
    "family_home": [f"{M}, {W} and {K} standing before a clay house with a blue door", "traditional Uzbek clay house with one carved blue wooden door and grape vine courtyard",
                    "warm lit windows of a small clay house at dusk, smoke from the chimney"],
    "wedding": [f"groom in white skullcap and bride in white dress with long veil, both seen from behind, under an arch of roses", "two golden wedding rings on white silk among rose petals",
                "courtyard decorated with garlands of roses and lanterns for a wedding"],
    "quarrel": ["broken blue ceramic tea bowl on a clay floor", f"{M} and {W} standing far apart with their backs to each other in a dim room", "lightning striking between two houses in a dark storm"],
    "gentle_love": [f"{M} gently embracing {K}, seen from behind, sunset field", f"{M} carrying {K} on his shoulders along a village road", "mother bird feeding chicks in a nest on a blooming branch"],
    "water_sapling": [f"{M} watering a tiny green sapling with a metal watering can in a garden", "tiny green sapling in dark soil with water drops, morning sun", "potter's wheel with a half finished clay jug in a workshop"],
    "deep_roots": ["giant old plane tree with massive exposed roots gripping the ground", "ancient mulberry tree with thick twisted roots on a hill"],
    "blossom": ["apricot tree in full pink bloom in a village courtyard", "orchard of blooming apricot trees in soft light, petals on the ground", "branch heavy with ripe golden apricots, close-up"],
    "time_hourglass": ["large hourglass with golden sand on a wooden table by a window", "old wooden hourglass on a stone ledge at sunset, sand running"],
    "calendar_day": ["sunrise over village rooftops, rooster on a clay wall", "village street at noon with strong shadows", "crescent moon over village rooftops at dusk"],
    "tired_bed": ["person asleep under a patchwork quilt on a wooden bed, dark room, moonlight", "unmade bed with patchwork quilts in a dim morning room"],
    "give_up": ["abandoned plough in an overgrown field", f"{M} walking away, leaving a half built brick wall behind", "withered plant in a cracked pot on a windowsill"],
    "prayer": [f"{M} kneeling on a prayer rug facing a tiled mihrab in a mosque", "row of men in white skullcaps bowing in prayer, seen from behind, mosque hall", "empty prayer rug by a window in dawn light"],
    "to_mosque": [f"{M} walking up the path to a mosque with a blue dome and minaret", "mosque with blue dome and tall minaret at dawn, birds flying", "open carved wooden gate of a mosque, warm light inside"],
    "dua": [f"{M} standing with raised arms under a vast starry sky", f"{M} sitting on a hill with raised open arms at sunrise"],
    "quran": ["closed ornate Quran with golden cover on a carved wooden stand, rays of light", "closed leather holy book with gold ornament on a carved stand beside a lamp"],
    "green_dome_night": ["green dome and white minaret of Medina under a starry night sky", "green dome and minarets of Medina mosque at dawn, birds"],
    "kaaba_scene": ["the Kaaba black cube with gold band, pilgrims in white seen from above, Mecca", "the Kaaba at night under bright lights, crowd of pilgrims in white"],
    "mercy_light": ["golden rays of sun breaking through clouds over a green valley", "gentle rain and rainbow over blooming meadow", "sunbeams falling through a huge tree onto a garden with a stream"],
    "sin_thorns": [f"{M} walking on a dark path between huge thorn bushes", "dark thorny thicket with a narrow path under a black sky", "deep dark pit in the middle of a road at night"],
    "grave": ["quiet old cemetery with simple stone graves and bare trees in mist", f"{M} standing beside a simple grave mound under a tree", "lone grave mound on a hill at sunset"],
    "reading": ["tall shelves full of old leather books in a warm library", "stack of old closed leather books beside an oil lamp", f"{M} standing before tall bookshelves"],
    "teach_child": [f"{M} and {K} sitting together at a low wooden table with closed books, seen from behind", f"old man in turban and {K} walking under an arch of a madrasa"],
    "phone_lecture": ["black smartphone lying face down on a dark table in blue light", f"{M} sitting in a dark room lit by blue light in front of him"],
    "sport": [f"man in tracksuit running along a morning road, seen from behind", "pair of iron dumbbells and running shoes on grass"],
    "diet": ["bowl of fresh green salad, tomatoes and a glass of water on a wooden table", "clear glass of water and green apples on a table by a window"],
    "mirror_self": [f"{M} standing before a tall framed mirror that reflects only light", "still lake like a mirror reflecting a lonely man standing on the shore, distant"],
    "question": [f"{M} standing at a crossroads of three paths in fog", f"{M} sitting alone on a rock looking at a wide foggy valley", "closed old wooden door at the end of a long stone corridor"],
    "money": ["big heap of shining gold coins spilling from a leather bag", "open wooden chest full of gold coins and jewels", "gold coins scattered on a dark wooden table"],
    "shop": ["bazaar stall with spices, fruits and textiles", "small village shop with sacks of flour and shelves of goods", "carpenter's workshop with wood shavings and tools"],
    "car_street": ["white car driving on a tree lined city street, seen from behind", "white car on a mountain road, seen from above"],
    "two_paths": [f"{M} standing before a fork in the road, one path green and sunny, the other dark and dry", "road splitting in two through hills at dawn"],
    "scale_deeds": ["large brass balance scales on a table, one pan lower", "old brass balance scales against a dark background, beam of light"],
    "gift": ["gift box wrapped in green cloth with golden ribbon", f"{M} handing a basket of bread to an old woman at a door, seen from behind"],
    "people": ["crowd of men in white skullcaps in a bazaar street, seen from behind", "people walking through a wide city square, seen from above"],
    "heart_scene": ["single red rose glowing in soft light, dark background", "glowing lantern burning in a dark stone niche", "clear spring of water flowing between stones"],
    "gambling": ["two white dice and a pile of gold coins on a green cloth table", "roulette wheel in dark smoky light", "slot machine glowing in a dark room"],
    "football": ["soccer ball on the grass of a stadium at night, floodlights", f"{M} watching a soccer match from the stands, huge green stadium", "soccer goal net with a black and white ball inside"],
    "hook_trap": ["big steel fishing hook with a gold coin as bait in dark water", "bird trapped in a wooden cage, dark room", "mouse trap with a piece of cheese on a wooden floor"],
    "honest_work": ["farmer in white skullcap seen from behind ploughing a field at sunrise", "golden wheat field with a farmer seen from behind holding a sickle", "strong worn hand tools, hammer and saw, on a workbench"],
    "enemy": ["wolf standing in the dark at the edge of a forest, glowing moon", f"{M} facing a huge dark storm cloud in an empty field", "black snake coiled on a path in tall grass"],
    "take_money": [f"{M} walking away on a road at dusk with a heavy leather bag", "leather bag full of gold coins on a doorstep"],
}


# object pictures for scenes that otherwise need people: used when the people cannot be painted without a face
OBJECTS = {
    "father_son": ["pair of big black boots and a pair of tiny red children's boots side by side on a doorstep", "big tree sheltering a small young tree beside it on a green hill",
                   "big bird and a small chick together on a blooming branch"],
    "advice_repeat": ["water drops falling on a hollowed stone, close-up", "lantern lighting a forked village path at dusk"],
    "not_listening": ["red ball lying alone in an empty courtyard", "closed wooden gate with an iron lock"],
    "gentle_love": ["mother bird feeding chicks in a nest on a blooming branch"],
    "dua": ["vast starry sky over a quiet mosque with a lit window", "empty prayer rug on a hill at sunrise"],
    "to_mosque": ["mosque with blue dome and tall minaret at dawn, birds flying"],
    "teach_child": ["small wooden table with stacked closed books and a lamp in a madrasa room", "two pairs of shoes, big and tiny, before a madrasa door"],
    "question": ["road fork with three empty paths in fog", "closed old wooden door at the end of a long stone corridor"],
    "mirror_self": ["tall framed mirror in a dim room reflecting a window's light"],
    "two_paths": ["road splitting in two through hills at dawn"],
    "honest_work": ["strong worn hand tools, hammer and saw, on a workbench"],
    "enemy": ["wolf standing in the dark at the edge of a forest, glowing moon"],
    "take_money": ["leather bag full of gold coins on a doorstep"],
    "people": ["wide bazaar street with many awnings and stalls, seen from above"],
    "wedding": ["two golden wedding rings on white silk among rose petals"],
}


def objects(scene, used=()):
    """variants of the scene without any people"""
    v = OBJECTS.get(scene, []) + [x for x in ART.get(scene, []) if not any(p in x for p in (M, W, K)) and "man" not in x.split() and "men" not in x.split()]
    v = list(dict.fromkeys(v))
    return [x for x in v if x not in used] or v


def scene_of(prompt):
    return next((k for k, v in ART.items() if prompt in v), "")


def choose(scene, used):
    """first variant of the scene that the last reels did not show"""
    v = ART.get(scene) or []
    return next((x for x in v if x not in used), v[len(used) % len(v)] if v else "")
