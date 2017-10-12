import copy
from ckan.plugins import toolkit as tk


def qa_openness_stars_resource_html(resource):
    qa = resource.get('qa')
    if not qa:
        return tk.literal('<!-- No qa info for this resource -->')
    if not isinstance(qa, dict):
        return tk.literal('<!-- QA info was of the wrong type -->')

    # Take a copy of the qa dict, because weirdly the renderer appears to add
    # keys to it like _ and app_globals. This is bad because when it comes to
    # render the debug in the footer those extra keys take about 30s to render,
    # for some reason.
    extra_vars = copy.deepcopy(qa)
    return tk.literal(
        tk.render('qa/openness_stars.html',
                  extra_vars=extra_vars))


def qa_openness_stars_dataset_html(dataset):
    qa = dataset.get('qa')
    if not qa:
        return tk.literal('<!-- No qa info for this dataset -->')
    if not isinstance(qa, dict):
        return tk.literal('<!-- QA info was of the wrong type -->')
    extra_vars = copy.deepcopy(qa)
    return tk.literal(
        tk.render('qa/openness_stars_brief.html',
                  extra_vars=extra_vars))

def qa_openness_stars_resource_line(resource):
    qa = resource.get('qa')
    if not qa:
        return tk.literal('<!-- No qa info for this resource -->')
    if not isinstance(qa, dict):
        return tk.literal('<!-- QA info was of the wrong type -->')
    extra_vars = copy.deepcopy(qa)
    return tk.literal(
        tk.render('qa/openness_stars_line.html',
                  extra_vars=extra_vars))

def qa_openness_stars_resource_table(resource):
    qa = resource.get('qa')
    if not qa:
        return tk.literal('<!-- No qa info for this resource -->')
    if not isinstance(qa, dict):
        return tk.literal('<!-- QA info was of the wrong type -->')
    extra_vars = copy.deepcopy(qa)
    return tk.literal(
        tk.render('qa/openness_stars_table.html',
                  extra_vars=extra_vars))
