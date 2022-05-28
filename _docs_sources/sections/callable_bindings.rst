.. _environments:

Callable bindings
============

The :code:`_callable` special kwarg allows you to provide a callable when
executing a command, or when :ref:`baking <baking>` a command. This is useful
when you want to parse the :code:`CommandResult` object returned by
:code:`sh`.

This can be useful when working with commands which return JSON or YAML as their
output, such as such as Google Cloud's `gcloud` or AWS' `aws` tool. To
illustrate its usage, consider an example of two `gcloud` commands. (You don't
need to understand what these commands do, apart from knowing the fact that
they return JSON as their output.)

.. code-block:: shell

    $ gcloud iam roles list --project=my-project --format json

    [
        {
            "description": "Ability to view or act on access approval requests",
            "name": "roles/accessapproval.approver",
            "title": "Access Approval Approver"
        },
        {
            "description": "Grants access to use all resource in Vertex AI",
            "name": "roles/aiplatform.user",
            "title": "Vertex AI User"
        }
    ]

    $ gcloud iam roles describe roles/accessapproval.approver --project=my-project --format json

    {
        "description": "Ability to view or act on access approval requests and view configuration",
        "includedPermissions": [
            "accessapproval.requests.approve",
            "accessapproval.requests.dismiss",
            "accessapproval.requests.get"
        ],
        "name": "roles/accessapproval.approver",
        "title": "Access Approval Approver"
    }

To work with this command's output in `sh`, you'd have to do something like
this:

.. code-block:: python

    from sh import gcloud

    roles_list = json.parse(str(gcloud.iam.roles.list(
        project='my-project', format='json')))

    role_info = json.parse(str(gcloud.iam.roles.describe(
        'roles/accessapproval.approver', project='my-project', format='json')))

Having to type out :code:`json.parse(str(..., project='...', format='json'))`
becomes repetitive quickly, so you can bake a command with the common arguments,
and a callable which would be invoked on the :code:`CommandResult` object
whenever you use :code:`sh` to run a command:

.. code-block:: python

    gcloud = sh.bake.gcloud.iam(format='json',
        project='my-project', _callable=lambda x: json.dumps(str(x)))

    # roles_list is a Python list object with the parsed output of 'gcloud iam roles list'
    roles_list = iam.roles.list()

    # Similarly, role_info is a Python dict object with the parsed output of 'gcloud iam roles describe'
    role_info = iam.roles.describe('roles/accessapproval.approver')

You can also add a callable to every individual command if you wish to:

.. code-block:: python

    roles_list = gcloud.iam.roles.list(
        project='my-project', format='json', _callable=lambda x: json.dumps(str(x)))
    role_info = gcloud.iam.roles.describe(
        'roles/accessapproval.approver',
        project='my-project', format='json', _callable=lambda x: json.dumps(str(x)))
