# CampusFix — Campus Service Request System (Lab 16 CEP Prototype)

A small Flask + SQLite web app that lets students report campus facility
problems (broken fans, leaking taps, lab issues) and lets maintenance
staff process the queue by priority.

## Features
- Register / login with roles (`student`, `staff`)
- Students: submit a request (title, category, location, description, priority), track status
- Staff: queue sorted by priority, update status (Submitted → In Progress → Resolved) with a resolution note
- Full status history stored per request (`status_update` table)

## Run
```bash
pip install -r requirements.txt
python app.py          # http://127.0.0.1:5000
```

Seeded demo accounts:
- student: `ali@student.uet.edu.pk` / `ali123`
- staff: `staff@uet.edu.pk` / `staff123`

## Tests
```bash
python -m unittest test_smoke -v
```

## Suggested commit history (already present in this repository)
1. `chore: project scaffold (README, requirements, license)`
2. `feat: database schema for users, categories, requests, status updates`
3. `feat: register and login with role-based sessions`
4. `feat: submit request flow with validation`
5. `feat: staff queue sorted by priority with status update`
6. `test: smoke tests for login and submit flows`
7. `ci: GitHub Actions workflow (install + smoke tests)`
