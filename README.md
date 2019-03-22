# Setting up

1. Make a virtual environment (don't call it `.env`!) and activate it.
2. `pip install wheel`
3. Install all dependencies by `pip install -r requirements.txt`.
4. Set environment variables in `.env`.
5. Initialize database by

```
> flask db init
> flask db migrate
> flask db upgrade
```