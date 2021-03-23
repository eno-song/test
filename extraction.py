from lxml import etree
import os, json
from tqdm import tqdm
SOURCE_PATH = './AMM_CHAPTERS'
ABB_LIST_PATH = open('./Abbreviation.json','r')
parser = etree.XMLParser(remove_blank_text=True)
xmls = [xml for xml in os.listdir(SOURCE_PATH) if xml.endswith('xml')]
task_level_list = []
subtask_level_list = []
abb_dict = json.loads(ABB_LIST_PATH.read())
abb_list = list(abb_dict.keys())
sub_count = 0

def handle_text(text):
	"""
	Function for handling text by replacing abbreviation with the full term
	Parameters:
		text: para text
	"""
	text_flag = False
	new_text = ''
	for ele in text.split(' '):
		if ele.strip() in abb_list:
			text_flag = True
			new_text = text[0:text.index(ele)] + abb_dict[ele.strip()] + text[text.index(ele)+len(ele):]
	if text_flag == False:
		new_text = text 	
	return new_text

def node_text(node):
	"""
	Function for adding node tail if needed
	Parameters:
		node: element
	"""
	if node.text:
		result = node.text
	else:
		result = ''
	for child in node:
		if child.tail is not None:
			result += child.tail
	result = handle_text(str(result))
	return result

def handle_sbeff_coceff(effect,tag_name,task_effrg,tagnbr,tagcond):
	"""
	Function for handling the tag EFFECT's children elements: SBEFF and COCEFF
	Parameters:
		effect: ISPEC tag EFFECT
		tag_name: sbeff or coceff
		task_effrg: a dictionary 
		tagnbr: sbnbr or cocnbr
		tagcond: sbcond or coccond
	"""
	temp_tag = effect.find('./' + tag_name)
	if temp_tag != None:
		task_effrg.update({tag_name.lower():{'effrg': temp_tag.get('EFFRG'),
									tagnbr.lower(): temp_tag.get(tagnbr),
									tagcond.lower(): temp_tag.get(tagcond)
		}})

def handle_effect(task):
	"""
	Function for handling the tag EFFECT:
	Parameters:
		task: ISPEC tag TASK
	"""
	task_effrg = {}
	for effect in task.findall('./EFFECT'):
		if effect.get('EFFRG') != None:
			task_effrg.update({'effect':{'effrg': effect.get('EFFRG')}})
		handle_sbeff_coceff(effect,'SBEFF',task_effrg,'SBNBR','SBCOND')
		handle_sbeff_coceff(effect,'COCEFF',task_effrg,'COCNBR','COCCOND')
	return task_effrg

def delete_tag_revend_and_revst(ele):

    '''
    Function for checking if tags <REVST> and <REVEND> exist
                 removing those two tags from ISPEC element (ele) if they exist
                 giving tail info of those two tags to the previous children element
    parameters:
        ele: ISPEC etree.Element
    '''
    for sub_ele in ele:
        if sub_ele.tag in ['REVST','REVEND']:
            if sub_ele.tail != None and ele.index(sub_ele) == 0:
                if ele.text is None:
                    ele.text = sub_ele.tail
                else:
                    ele.text += sub_ele.tail
            elif sub_ele.tail != None and ele.index(sub_ele) !=0:
                index_number = ele.index(sub_ele)
                if ele[(index_number-1)].tail != None and ele[(index_number-1)].tail != '':
                    total_tail = ele[(index_number-1)].tail + sub_ele.tail
                    ele[(index_number-1)].tail = total_tail
                else:
                    ele[(index_number-1)].tail = sub_ele.tail
            ele.remove(sub_ele)

def handle_para_tag(para,para_text):
	"""
	Function for handling the tag para
	Parameters:
		para: ISPEC tag PARA
		para_text: the tag's text
	"""
	delete_tag_revend_and_revst(para)
	if (para.text) not in [None,'']: 
		para_text += para.text
	for ele in para:
		delete_tag_revend_and_revst(ele)
		if ele.tag in ['REFBLOCK','REFEXT']: pass
		elif ele.tag in ['PAN','STDNAME','NCON','EIN']:
			para_text = handle_para_text(para_text,node_text(ele))
			para_text = handle_para_text(para_text,ele.tail)
		elif ele.tag in ['TED','CON','EXPD']:
			for sub_ted in ele:
				para_text = handle_para_text(para_text,node_text(sub_ted))
				para_text = handle_para_text(para_text,sub_ted.tail)
			para_text = handle_para_text(para_text,ele.tail)
		elif ele.tag == 'TOR':
			for torvalue in ele.findall('./TORVALUE'):
				for attrib in torvalue.attrib:
					para_text = handle_para_text(para_text,str(attrib) + ' ' + torvalue.get(attrib))
					para_text = handle_para_text(para_text,torvalue.tail)
			para_text = handle_para_text(para_text,ele.tail)
	para_text = handle_text(para_text)
	return para_text

def handle_para_text(para_text,text):
	"""
	Function for handling para text
	Parameters:
		para_text: element's text
		text: text elements need to be added after element's text
	"""
	if text not in [None,'']:
		if text not in ['.',',',';',':','!']:
			if para_text in ['',None]: 
				para_text += text
			else:
				if para_text[-1] == ' ' or text[0] == ' ':
					para_text += text
				else:
					para_text += ' ' + text
		else:
			para_text += para_text + text
	para_text = handle_text(para_text)
	return para_text.strip()

def handle_refblock(subtask):
	"""
	Function for handling of the tag REFBLOCK
	Parameters:
		subtask: ISPEC tag SUBTASK
	"""
	refblock_list = []
	for refblock in subtask.findall('.//REFBLOCK'):
		delete_tag_revend_and_revst(refblock)
		refblock_dict = {}
		if node_text(refblock) != None:
			refblock_dict.update({'refblock_id': node_text(refblock)})
			refblock_para = ''
			refblock_para = handle_para_tag(refblock.getparent(),refblock_para)
			refblock_para = handle_text(str(refblock_para))
			if 'MIN' in refblock_para.split(' '): print(refblock_para)
			refblock_dict.update({'refblock_para': refblock_para})
			refblock_dict.update({'refint':[]})
		for refint in refblock.findall('.//REFINT'):
			delete_tag_revend_and_revst(refint)
			refint_dict = {}
			if refint.get('REFID') != None:
				refint_dict.update({'refint_id': refint.get('REFID')})
				refint_dict.update({'refint_effrg': handle_effect(refint)})
			if refint_dict != {}: 
				refblock_dict['refint'].append(refint_dict)
		if refblock_dict != {}:
			refblock_list.append(refblock_dict)
	return refblock_list

def handle_subtask(subtask):
	"""
	Function for handling of tag subtask
	Parameters:
		subtask: ISPEC tag SUBTASK
	"""
	para_text = ""
	for para in subtask.find('./LIST1/L1ITEM'):
		if para.tag == 'PARA':
			para_text = handle_para_tag(para,para_text)
			break
	subtask_dict =  {	'subtask_id':subtask.get('KEY'),
						'subtask_title':handle_text(para_text),
						'subtask_effrg': handle_effect(subtask),
						'subtask_content':[]
					}	
	subtask_title = handle_text(para_text)
	for para in subtask.findall('.//PARA'):
		if para.getparent().tag != 'ENTRY':
			para_text = ''
			para_text = handle_para_tag(para,para_text)
			new_para_text = handle_text(para_text)
			if new_para_text != subtask_title and new_para_text not in subtask_dict['subtask_content']:
				subtask_dict['subtask_content'].append(new_para_text)
	if handle_refblock(subtask) != []:
		subtask_dict.update({'refblock': handle_refblock(subtask)})
	return subtask_dict

def extract_data_on_task_level(root):
	"""
	Function for extracting data on task level
	Parameters:
		root: ISPEC root element
	"""
	for task in root.findall('.//TASK'):
		if 'DELETED' not in [sub_task.tag for sub_task in list(task)]:
			task_dict = {	'task_id':task.get('KEY'),
							'task_title': node_text(task.find('./TITLE')),
							'task_effrg': handle_effect(task),
							'subtask': []
						}
			task_dict_1 = {}
			for subtask in task.findall('.//SUBTASK'):
				if 'DELETED' not in [child.tag for child in list(subtask)]:
					task_dict['subtask'].append(handle_subtask(subtask))
					task_dict_1.update({sub_count:subtask.get('KEY')})
			task_level_list.append(task_dict)
	
def extract_data_on_subtask_level(root):
	"""
	Function for extracting data on subtask level
	Parameters:
		root: ISPEC root element
	"""
	for subtask in root.findall('.//SUBTASK'):
		if 'DELETED' not in [sub_task.tag for sub_task in list(subtask)]:
			parent_task = subtask.getparent().getparent()
			added_dictionary = {
				'parent_task_id': parent_task.get('KEY'),
				'parent_task_title':node_text(parent_task.find('./TITLE')),
				'parent_task_effrg': handle_effect(parent_task)
			}
			dictMerged2=dict(added_dictionary,**handle_subtask(subtask))
			subtask_level_list.append(dictMerged2)

def print_result(file_name,generated_list):
	"""
	Function for printing result
	Parameters:
		file_name: output name
		generated_list: the list to be printed out
	"""
	with open('./output/'+ file_name,'w') as file:
			file.write(json.dumps(generated_list,indent=4))

if __name__ == '__main__':
	for xml in tqdm(xmls):
		root = (etree.parse(SOURCE_PATH+'/'+xml, parser=parser)).getroot()
		extract_data_on_task_level(root)	
		extract_data_on_subtask_level(root)
	print_result('task_based_data_extraction.json',task_level_list)
	print_result('subtask_based_data_extraction.json',subtask_level_list)	
		
	
		