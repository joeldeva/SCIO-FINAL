def capabilities():
    return {'translation_is_separate_from_recognition': True, 'recognition_systems': [
        {'id':'english-letters','name':'English letters a–z','enabled':True,'model_classes':list('abcdefghijklmnopqrstuvwxyz'),
         'limitations':'Camera recognition of capitals, digits, punctuation and Grade 2 contractions is not validated.'},
        {'id':'bharati','name':'Bharati Braille','enabled':False,'model_classes':[], 'limitations':'Requires models, rules and independent validation.'},
        {'id':'ueb-contracted','name':'Contracted English Braille','enabled':False,'model_classes':[], 'limitations':'Learning content exists; camera recognition is not validated.'}]}
