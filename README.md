## Library for Running Aqara Scenes
To use this library, you need to register as a developer in the Aqara cloud: https://developer.aqara.com/.
Make sure to use the email (account) linked to your smart home system.

After registration, a project with authentication credentials (app_id, app_key, key_id) will be automatically created.

The scene ID can be obtained in the "V3.0 API list" tab under the Scene Management category.

Important Note:
During the first launch, the code for obtaining tokens is sent to the account's email.
Once received, create a code.json file in the state_dir directory with the following content:
```
{'code': email_code}
```
Alternatively, you can use the save_code method of the class.

On subsequent launches, the code will be exchanged for tokens, and everything will work correctly.
The Refresh Token is valid for 30 days. If it is not exchanged in time, a new code will be sent to the email again.

## Install
```bash
pip install -e .
```

## Usage
```python
from aqara_scene_runner.app import AqaraSceneRunner

runner = AqaraSceneRunner(
    app_id='Your app_id',
    app_key='Your app_key',
    key_id='Your key_id',
    account='Your aqara email',
    state_dir='Direcory for tokens'
)

runner.run_scene(scene_id='scene_id')
```