# Lessons Learned: Building Anki .apkg Files Programmatically

A collection of problems encountered and solutions found while building Anki decks with embedded images.

## Problem 1: Images show as text filenames

**Symptom:** Cards display `Ambika_Devi_Sangraula.jpg` as plain text instead of rendering the image.

**Root Cause:** The `<img>` tag must go in the **field value**, not in the template. Anki templates with `{{Field}}` just output the field content as-is. If the field contains `photo.jpg`, Anki renders the literal text `photo.jpg`.

**Solution:**
```python
# WRONG - field contains just filename
fields=['Name', 'photo.jpg']
# Template: <img src="{{Photo}}">  ← This outputs "<img src="photo.jpg">" as TEXT

# CORRECT - field contains the full HTML tag
fields=['Name', '<img src="photo.jpg" width="200">']
# Template: {{Photo}}  ← This outputs the actual HTML which Anki renders
```

**Source:** [genanki README](https://github.com/kerrickstaley/genanki) states:
> "You *cannot* put `<img src="...">` in the template and `my_image_file.jpg` in the field."

---

## Problem 2: Missing `id` field in model/deck/dconf JSON

**Symptom:** `JsonError { info: "decoding models: missing field 'id'" }`

**Root Cause:** Anki's Rust-based parser requires an `id` field in all JSON objects (models, decks, deck configs). This isn't documented but is enforced at parse time.

**Solution:**
```python
model = {
    "id": 1607392319,      # ← Required
    "name": "My Model",
    ...
}

deck = {
    "id": 2059400110,      # ← Required
    "name": "My Deck",
    ...
}

dconf = {
    "1": {
        "id": 1,            # ← Required
        "usn": -1,          # ← Also required
        ...
    }
}
```

---

## Problem 3: Missing `usn` field in deck config

**Symptom:** `JsonError { info: "decoding deck config: missing field 'usn'" }`

**Root Cause:** The `usn` (update sequence number) field is required in deck config objects. Use `-1` for "not yet synced".

**Solution:** Add `"usn": -1` to all deck config entries.

---

## Problem 4: Missing `graves` table

**Symptom:** `DbError { info: "no such table: graves" }`

**Root Cause:** Anki's v11 schema expects a `graves` table (for tracking deleted items). Without it, Anki refuses to open the database.

**Solution:** Create the table even if empty:
```sql
CREATE TABLE graves (
    usn integer not null,
    oid integer not null,
    type integer not null
)
```

---

## Problem 5: Meta file format (Protobuf vs JSON)

**Symptom:** `ProtoError { info: "failed to decode Protobuf message: buffer underflow" }`

**Root Cause:** The `meta` file in Legacy 2 format must be Protobuf-encoded, not JSON. Modern Anki expects specific binary format.

**Solution:** For maximum compatibility, use Legacy 1 format (no `meta` file):
- Just `collection.anki2` + `media` + numbered files
- Or use genanki which handles this correctly

---

## Problem 6: Media file mapping format

**Symptom:** Images don't load despite being in the .apkg file.

**Root Cause:** The `media` file maps numeric string keys ("0", "1", "2"...) to actual filenames. The note fields must contain filenames that match the media mapping values.

**Solution:**
```json
// media file
{"0": "photo.jpg", "1": "logo.png"}

// Note field must contain "photo.jpg", NOT "0"
fields=['Name', '<img src="photo.jpg">']
```

---

## Problem 7: genanki image handling

**Symptom:** genanki creates .apkg but images don't render in Anki.

**Root Cause:** genanki's image handling requires a specific pattern that's not obvious from the API.

**Solution:**
```python
# 1. Copy images to a temp directory
# 2. Set media_files to full paths of images
# 3. Put <img src="filename.ext"> in the field value
# 4. Template just outputs {{FieldName}} directly

model = genanki.Model(
    model_id,
    'My Model',
    fields=[
        {'name': 'Name'},
        {'name': 'Photo'},  # Will contain <img src="...">
    ],
    templates=[{
        'name': 'Card 1',
        'qfmt': '{{Name}}',
        'afmt': '{{FrontSide}}<hr>{{Photo}}',  # Just {{Photo}}, no <img> tag here
    }],
)

note = genanki.Note(model=model, fields=['John', '<img src="john.jpg" width="200">'])
package = genanki.Package(deck)
package.media_files = ['/full/path/to/john.jpg']  # Full paths
package.write_to_file('output.apkg')
```

---

## Problem 8: SSL certificate errors when downloading images

**Symptom:** `curl: (60) SSL certificate problem: unable to get local issuer certificate`

**Root Cause:** Some servers have certificate chain issues.

**Solution:**
```python
import ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx) as response:
    data = response.read()
```

---

## Problem 9: Anki schema version compatibility

**Observation:** Anki has evolved through multiple schema versions:
- v11: Legacy 1 format (collection.anki2)
- v14-v17: Transitional (collection.anki21)
- v18: Latest (collection.anki21b, protobuf)

**Recommendation:** Stick with v11 (Legacy 1) for maximum compatibility:
- Just `collection.anki2` + `media` + numbered files
- Works with all Anki versions
- No Protobuf dependencies

---

## References

- [genanki](https://github.com/kerrickstaley/genanki) - Python library for generating Anki decks
- [Understanding the Anki APKG Format](https://eikowagenknecht.com/posts/understanding-the-anki-apkg-format/) - Comprehensive format documentation
- [AnkiDroid Database Structure](https://github.com/ankidroid/Anki-Android/wiki/Database-Structure) - Schema reference
- [Anki Source Code](https://github.com/ankitects/anki) - Official Anki repository
