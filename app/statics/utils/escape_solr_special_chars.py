def escape_solr_special_chars(text):
    """Échapper les caractères spéciaux pour Solr"""
    special_chars = ['+', '-', '&&', '||', '!', '(', ')', '{', '}', '[', ']', '^', '"', '~', '*', '?', ':', '\\', '/']
    
    # Ajouter des caractères spéciaux supplémentaires au besoin
    special_chars.extend(['ü', 'ä', 'ö'])
    
    # Échapper les caractères spéciaux
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    # Échapper les espaces avec des guillemets doubles pour Solr
    text = text.replace(' ', r'\ ')
    
    return text
