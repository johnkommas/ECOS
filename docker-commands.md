### ECOS — Ready-to-use Docker Compose commands

Copy/paste commands adapted for this project.

- Project folder: `/Users/johnkommas/PycharmProjects/ECOS`
- Service URL: http://localhost:8002

---

#### Γρήγορη εκκίνηση (τρέχοντας μέσα στο project)
```bash
cd /Users/johnkommas/PycharmProjects/ECOS
# build + start (detached)
docker compose -f docker-compose.yml up -d --build
```

Όταν αλλάζουν dependencies (requirements) ή θέλεις πλήρες καθάρισμα cache:
```bash
cd /Users/johnkommas/PycharmProjects/ECOS
# rebuild χωρίς cache (και pull νεότερες βάσεις)
docker compose -f docker-compose.yml build --pull --no-cache
# αναδημιουργία container
docker compose -f docker-compose.yml up -d --force-recreate
```

Χρήσιμες βοηθητικές εντολές:
```bash
# Ζωντανά logs
docker compose -f docker-compose.yml logs -f
# Έλεγχος κατάστασης
docker compose -f docker-compose.yml ps
# Ολικό stop & remove
docker compose -f docker-compose.yml down
# (Προαιρετικό) καθάρισμα και volumes
docker compose -f docker-compose.yml down -v
```

Σημείωση: Αν βρίσκεσαι ήδη στον φάκελο του project, το `-f docker-compose.yml` είναι προαιρετικό.

---

#### Εκτέλεση με απόλυτο path στο compose file (χωρίς `cd`)
```bash
# build + start (detached)
docker compose -f /Users/johnkommas/PycharmProjects/ECOS/docker-compose.yml up -d --build
# clean rebuild (no cache)
docker compose -f /Users/johnkommas/PycharmProjects/ECOS/docker-compose.yml build --pull --no-cache
# force recreate containers
docker compose -f /Users/johnkommas/PycharmProjects/ECOS/docker-compose.yml up -d --force-recreate
# helpers
docker compose -f /Users/johnkommas/PycharmProjects/ECOS/docker-compose.yml logs -f
docker compose -f /Users/johnkommas/PycharmProjects/ECOS/docker-compose.yml ps
docker compose -f /Users/johnkommas/PycharmProjects/ECOS/docker-compose.yml down
```

---

#### Προαιρετικά (αν τρέχεις και άλλο stack με κοινό project name)
Μπορείς να ορίσεις όνομα στο Compose project για να διαχωρίσεις δίκτυα/volumes:
```bash
# Παράδειγμα με κοινό όνομα project (π.χ. "stack")
docker compose -p stack -f /Users/johnkommas/PycharmProjects/ECOS/docker-compose.yml up -d --build
```

Για να σταματήσεις/καθαρίσεις αυτό το συγκεκριμένο project name:
```bash
docker compose -p stack -f /Users/johnkommas/PycharmProjects/ECOS/docker-compose.yml down
```

---

#### Tips
- Βεβαιώσου ότι το `.env` υπάρχει στο root του project — το Compose το φορτώνει αυτόματα (env_file).
- Αν η πόρτα 8000 είναι πιασμένη, άλλαξε mapping στο `docker-compose.yml` (π.χ. `8080:8000`) και άνοιξε http://localhost:8080.
- Για πλήρες καθάρισμα cache εικόνων μετά από μεγάλες αλλαγές:
```bash
docker builder prune -f
```

---

Για περισσότερες λεπτομέρειες, δες επίσης: `docker.md`.
