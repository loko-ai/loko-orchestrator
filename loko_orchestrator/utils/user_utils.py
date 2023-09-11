import os, grp


def get_docker_group():
    for id in os.getgroups():
        if grp.getgrgid(id).gr_name == "docker":
            return id
    return None
