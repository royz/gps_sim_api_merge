#### There's need to be `config.py` file with the following fields

```python
# Navixy config
navixy_accounts = [
    {
        'username': 'username1@email.com',
        'password': 'passwd'
    },
    {
        'username': 'username2@email.com',
        'password': 'passwd'
    },
]

# Things Mobile Config
things_mobile_username = ''
things_mobile_token = ''

# User Config
outer_loop_time = 7200  # 2 hours
inner_loop_time = 300  # 5 minutes
```
