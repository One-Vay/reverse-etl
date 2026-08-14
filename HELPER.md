## 🌿 Как создавать ветки и использовать GitHub Flow (пошаговая инструкция)

### 🧱 1. Структура веток (GitHub Flow)

```
main (стабильная, всегда рабочая)
  ↑
  └── feature/add-login (новая фича)
  └── fix/bug-123 (исправление)
  └── docs/readme-update (документация)
```

Все новые изменения делаются **в отдельных ветках**, затем создаётся **Pull Request** → после проверки → слияние в `main`.

---

### 🚀 2. Как создать новую ветку (локально)

```bash
# Переключиться на main и подтянуть последние изменения
git checkout main
git pull origin main

# Создать новую ветку (пример: feature/add-login)
git checkout -b feature/add-login

# (или с длинным описанием)
git checkout -b feature/authentication-implementation
```

---

### 💻 3. Работа в ветке

```bash
# Делаете изменения, коммитите
git add .
git commit -m "Add login form"

# Несколько коммитов в ветке
git commit -m "Add password hashing"
git commit -m "Add JWT token generation"

# Периодически подтягивайте изменения из main, чтобы не было конфликтов
git pull origin main --rebase   # или просто git merge main
```

---

### 📤 4. Отправить ветку на GitHub

```bash
git push origin feature/add-login
```

После первого пуша появится ссылка для создания Pull Request.

---

### 🔁 5. Создать Pull Request (через GitHub)

- Перейти на страницу репозитория → **Pull requests** → **New pull request**
- Выбрать: `base: main` ← `compare: feature/add-login`
- Добавить описание, что сделано, зачем, как тестировалось.
- Нажать **Create pull request**.

Если настроены CI-проверки, они запустятся автоматически.

---

### ✅ 6. Проверка и слияние

- Вы (или другие разработчики) смотрят код, оставляют комментарии.
- Если всё хорошо, нажимаете **Merge pull request** → **Confirm merge**.
- Ветка автоматически удаляется (или можно удалить вручную).

---

### 🗑️ 7. Удалить локальную ветку (после слияния)

```bash
git checkout main
git pull origin main           # обновить локальный main
git branch -d feature/add-login  # удалить локальную ветку
```

---

### 📋 8. Когда использовать разные префиксы

| Префикс | Пример | Назначение |
|---------|--------|------------|
| `feature/` | `feature/user-profile` | Новая функциональность |
| `fix/` | `fix/login-error` | Исправление бага |
| `docs/` | `docs/api-reference` | Обновление документации |
| `chore/` | `chore/update-deps` | Вспомогательные задачи (обновление зависимостей, настройка CI) |
| `refactor/` | `refactor/auth-service` | Рефакторинг без изменения логики |

---

### 🛡️ 9. Настройка защиты ветки `main` (через GitHub)

1. Зайдите в репозиторий → **Settings** → **Branches**.
2. В разделе **Branch protection rules** → **Add rule**.
3. В поле **Branch name pattern** введите `main`.
4. Выберите опции:
   - ✅ **Require a pull request before merging**
   - ✅ **Require approvals** (поставьте 1)
   - ✅ **Require status checks to pass before merging** (выберите ваши CI-задачи)
   - ✅ **Require branches to be up to date before merging**
5. Нажмите **Create**.

Теперь никто не сможет пушить напрямую в `main`, только через PR с прохождением проверок.

---

### 💡 Советы для open-source

- **Именуйте ветки кратко, но понятно**: `feature/oauth-google` лучше, чем `feature/new-thing`.
- **В PR описывайте изменения**, особенно если есть breaking changes.
- **Не забывайте обновлять документацию** при добавлении новых фич.
- **Если вы один разработчик**, PR всё равно полезен – вы сами проверяете свой код как бы "со стороны".
- **Используйте шаблоны PR** (можно добавить файл `.github/pull_request_template.md`), чтобы автоматически подставлять структуру описания.

---

### ✅ Итог

- Все изменения – в отдельных ветках от `main`.
- Ветки именуются по схеме `тип/описание`.
- Изменения попадают в `main` только через Pull Request.
- Защита `main` включена, CI-проверки обязательны.

Это дисциплинирует, упрощает поиск багов и позволяет легко откатить изменения, если что-то пошло не так. В open-source такая практика обязательна, чтобы сохранять качество кода. Удачи! 🚀