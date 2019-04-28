from bs4 import Tag, NavigableString

def clone_beautiful_soup_tag(element):
    if isinstance(element, NavigableString):
        return type(element)(element)

    copy = Tag(None, element.builder, element.name, element.namespace, element.nsprefix)
    # work around bug where there is no builder set
    # https://bugs.launchpad.net/beautifulsoup/+bug/1307471
    copy.attrs = dict(element.attrs)
    for attr in ('can_be_empty_element', 'hidden'):
        setattr(copy, attr, getattr(element, attr))
    for child in element.contents:
        copy.append(clone_beautiful_soup_tag(child))
    return copy
