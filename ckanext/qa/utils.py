"""
Utils for new and old cli
"""


def init_db():
    import ckan.model as model
    from ckanext.qa.model import init_tables
    init_tables(model.meta.engine)