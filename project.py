#!/usr/bin/env python
# coding: utf-8

# # DeltaDebugging Algorithm in context of LaTeX files

# Nina Braunmiller<br>
# k11923286<br>
# k11923286@students.jku.at<br>
# <br>
# Institute for Symbolic Artificial Intelligence<br>
# Johannes Kepler University Austria<br>
# <br>
# 12th March 2024

# In[20]:


import numpy as np
import re

import subprocess
from subprocess import PIPE
import os, shutil

import time

from pylatexenc.latexwalker import LatexWalker, LatexMacroNode, LatexCharsNode, LatexCommentNode, LatexSpecialsNode, LatexEnvironmentNode, LatexGroupNode, LatexMathNode 


# In[21]:


def open_full_file_as_string(file_name):
    '''
    returns string with \\command{} structure
    '''

    with open(file_name, 'r') as f:
        
        raw_string = f.read()
    
    return raw_string


# In[22]:


def looper_over_string(string, start_ind_val):
    '''
    finds the content of \\command{content}
    
    params: 
    string -> input string
    start_ind_val -> starting index at the string
    
    returns: 
    found_string -> first command part found, e. g. text\\command{content}
    jump_over_string -> rest of the input string after found_string
    final_ind -> index where the found_string stops in the inputted string
    inner_command_text -> content of found_string
    '''
    
    string = string[start_ind_val:]

    found_string = r''
    jump_over_string = r''
    open_counter = 0
    final_ind = -1
    
    start_ind = 0
    
    for ind_char, char in enumerate(string):
        
        if char == '{':
            
            open_counter += 1
            start_ind = ind_char + 1

        elif char == '}' and open_counter == 1:
            
            final_ind = ind_char
            
            if final_ind<len(string)-1:
                
                jump_over_string = string[final_ind+1:]
            
            break
            
        elif char == '}':
            
            open_counter -= 1
    
    inner_command_text = string[start_ind:final_ind]
        
            
    found_string = string[:final_ind+1]
    final_ind += start_ind_val

    return found_string, jump_over_string, final_ind, inner_command_text


# In[23]:


def commandlist_finder(raw_string, start_content_comment='document', normal_outer_command=False):
    '''
    shall create a list of deltas/commands which are encoded as strings. This counts only for the center
    (the body of the environment of the start_content_comment). The front and back skeleton which 
    enclose the searched environment are kept stable and each is stored as one element in the front and 
    back of the command list.
    
    params:
    raw_string -> the input string
    start_content_comment -> which content marks the end/start of the preamble/back skeleton
    normal_outer_command -> boolean which marks the start_content_comment as part of environment command
                            (False) or as other form of command, e. g. math or \\command{} (True)
    
    returns:
    command_list -> list which contains the separated deltas/commands
    start_content_ind -> where the center of interest starts (inner nest or body)
    end_content_ind -> where the center of interest ends (inner nest or body)
    nested_commands -> boolean list which states whether the command_list elements are nested commands (True)
                       or not (False)
    '''
    
    # make one list with full file as content
    if start_content_comment is not None: 
        
        body_start_pattern = '\\begin{' + start_content_comment + '}'
        
        if normal_outer_command:
            
            body_start_pattern = start_content_comment
            
        try: 
            # mark index where we start:
            
            body_start_index = raw_string.index(body_start_pattern) + len(body_start_pattern)
            start_content_ind = 0 

        except:
            
            body_start_index = 0
            start_content_ind = -2 
            # when one of these are missed to modify, the center_content will be []

        if normal_outer_command:
            
            rev = "".join(reversed(raw_string))

            if '\\(' == start_content_comment:
                
                rev_ind = rev.find(')\\')
                
                if rev_ind == -1:
                    return f'Math environment does not close: round brackets; considered string part: {raw_string}', None, None, None
                
                body_end_index = (-1) * rev_ind - 1 - 2 + 1

            elif '\\[' == start_content_comment:

                rev_ind = rev.find(']\\')
                
                if rev_ind == -1:
                    return f'Math environment does not close: square brackets; considered string part: {raw_string}', None, None, None
                
                body_end_index = (-1) * rev_ind - 1 - 2 + 1
                
            elif '$' == start_content_comment:
                
                rev_ind = rev.find('$')
                
                if rev_ind == -1:
                    return f'Math environment does not close: $; considered string part: {raw_string}', None, None, None
                
                body_end_index = (-1) * rev_ind - 1
                
            elif '$$' == start_content_comment:
                
                rev_ind = rev.find('$$')
                
                if rev_ind == -1:
                    return f'Math environment does not close: $$; considered string part: {raw_string}', None, None, None
                
                body_end_index = (-1) * rev_ind - 1 - 1

            
            else:
                
                rev_ind = rev.find('}')
                
                if rev_ind == -1:
                    return f'Group or normal environment does not close: curly closing bracket; considered string part: {raw_string}', None, None, None
                
                body_end_index = (-1) * rev_ind - 1
                
            end_content_ind = -1

        else:
            
            body_end_pattern = '\\end{' + start_content_comment + '}'

            try:
                
                body_end_index = raw_string.index(body_end_pattern)
                end_content_ind = -1
                
            except:
                
                body_end_index = len(raw_string)
                end_content_ind = 0        
        
    else:
        
        body_start_index = 0
        start_content_ind = -2   
        body_end_index = len(raw_string)
        end_content_ind = 0
        
    
    front_string = raw_string[:body_start_index]

    center_string = raw_string[body_start_index : body_end_index]

    back_string = raw_string[body_end_index:]

    w_center = LatexWalker(center_string)
    (nodelist_center, pos, len_) = w_center.get_latex_nodes(pos=0)

    if len(front_string)>0:
        
        command_list = [front_string]
        nested_commands = [False] 
        
    else:
        
        command_list = []
        nested_commands = []  
            
    command_marker = False

    for node in nodelist_center:
        # check for nested structure:
        # overview node types in LatexWalker: https://pylatexenc.readthedocs.io/en/latest/latexnodes.nodes/

        if node.isNodeType(LatexMacroNode):
            '''
            special case:
            a) \\NONEXIST{content}
            b) \\EXIST{content}{group}
            -> The {content} of a) shall not be seen as group as we don't want to split it further in the
            normal delta_splitter process. Therefore, use:
            '''

            if node.nodeargd != None:
                
                if node.nodeargd.argnlist == []: # a) \\NONEXIST is the case
                    
                    command_marker = True
                    
                else: 
                    
                    command_marker = False
                    
            else: 
                
                command_marker = False            

            list_nodelists = re.findall('nodelist',str(node))
            
            if len(list_nodelists) > 1: # already a simple command contains a nodelist, eg \\hat{} --> [] .
                
                nested_commands.append(True)
            
            else:
                
                nested_commands.append(False)

        elif node.isNodeType(LatexCharsNode) or node.isNodeType(LatexCommentNode) or node.isNodeType(LatexSpecialsNode):
            
            nested_commands.append(False)
            command_marker = False
            
            
        elif node.isNodeType(LatexGroupNode):
            
            if len(node.nodelist) > 0 and not command_marker:
                
                nested_commands.append(True)
                
            else:
                
                nested_commands.append(False)
                
            command_marker = False

        elif node.isNodeType(LatexEnvironmentNode) or node.isNodeType(LatexMathNode):
            
            if len(node.nodelist) > 0:
                
                nested_commands.append(True)
                
            else:
                
                nested_commands.append(False)
                
            command_marker = False
                       
        else:

            nested_commands.append(False)
            command_marker = False
            
        # store string format:
        command_list.append(node.latex_verbatim())
            
    if len(back_string) > 0:        
        
        command_list.append(back_string)
        nested_commands.append(False)  
        
    return command_list, start_content_ind, end_content_ind, nested_commands  


# In[24]:


def content_creator(command_list, first_begin_ind, last_end_ind):
    '''
    splits a list of commands into three parts 
    
    params:
    command_list -> list of commands/deltas
    first_begin_ind -> index where the body or center of interest starts
    last_end_ind -> index where the center of interest or body ends
    
    returns:
    front_skeleton -> preamble or front skeleton of the center of interest
    center_content -> body or center of interest
    back_skeleton -> closing \\end{document} and follwoing text or back skeleton of the center of interest    
    '''
    
    # define skleton next which has to be reused in every round:
    front_skeleton = command_list[:first_begin_ind+1]
    center_content = command_list[first_begin_ind+1:last_end_ind]
    back_skeleton = command_list[last_end_ind:]
    
    return front_skeleton, center_content, back_skeleton 


# In[25]:


def latex_failure_check(log_file_image_path, container_name, project_folder): 
    '''
    reads the .log file created by pdfLaTeX to get the error message.
    
    params:
    log_file_image_path -> path within the Docker image where the .log file is stored
    container_name -> container name which is the instance of the Docker image
    project_folder -> the outer folder name where to store the .log file 
    
    returns error_message -> found error message as string
    
    '''
    
    # One specific file can be copied FROM the container like:
    dest_folder = project_folder + '/logs_from_container' + '/' + log_file_image_path.split('/')[-2]
    os.makedirs(dest_folder, exist_ok=True)
    dest = dest_folder + '/' + log_file_image_path.split('/')[-1]

    # copy the .log file from Docker image to host:
    subprocess.run(['docker', 'cp', '' + container_name + ':' +  log_file_image_path , dest])
    # container_name:path_image, path_host
    
    # find out specific error message such that we can distinguish between failing ('x') and 
    # unspecified ('?') test:
    with open(dest, 'r') as f: 

        content = f.read()
        error_string = '! ' 
                    
        found = re.search(error_string, content)

        if found is not None:

            to = content[found.start():].index('\n') 
            to += found.start()+1

            error_message = content[found.start():to]

        else:

            error_message = ''
            
    print('Found error:', error_message)
    
    return error_message


# In[26]:


def delta_splitter(command): 
    '''
    param command as nested command from which we want to remove the outer command shell
    
    returns:
    center_content_delta ->  list containing the content of a command
    nested_commands_center ->  list describing if elements of center_content_delta are nested (True) or not (False)
    found_commands_delta[:first_begin_ind_delta+1] -> front part/shell of the nest
    found_commands_delta[last_end_ind_delta:] -> back part/shell of the nest
    
    e. g.
    for command = '\\begin{a}\\begin{b}\\text{o}textbetween\\end{b}\\end{a}' it returns ['\\begin{b}\\text{o}textbetween\\end{b}'], [True],  ['\\begin{a}'], ['\\end{a}'].
    for command = '\\begin{b}\\text{o}textbetween\\end{b}' it returns ['\\text{o}','textbetween'], [False, False], ['\\begin{b}'], ['\\end{b}'].
    for command = '\\command{any}text' it returns ['any'], [False], ['\\command{'], ['}text'].
    for command = '\\command{any}' it returns ['any'], [False], ['\\command{'], ['}'].
   '''


    # get the command content which we want to delete:
    found_string, jump_over_string, final_ind, inner_command_text = looper_over_string(command, 0)

    tag = False
    command_match = re.search(r'\\', command) # use this to find out the index of the first command
    command_match2 = re.search(r'$', command) # use this to find out the index of the first command

    if command_match is not None or command_match2 is not None:
        
        if command_match is not None and command_match2 is not None:
            
            command_match_start_ind = command_match.start()
            command_match_start_ind2 = command_match2.start()
            if_str = command[command_match_start_ind:command_match_start_ind+1+5]
            
        elif command_match is not None:
            
            command_match_start_ind = command_match.start()
            command_match_start_ind2 = float('inf')
            if_str = command[command_match_start_ind:command_match_start_ind+1+5]
            
        elif command_match2 is not None:
            
            command_match_start_ind = float('inf')
            command_match_start_ind2 = command_match2.start()
            if_str = command[command_match_start_ind2:command_match_start_ind2+1] # 'anything'

        command_match_group = re.search(r'{', command)
        
        if command_match_group is not None:
            
            command_group_start_ind = command_match_group.start()
            
            if command_group_start_ind < command_match_start_ind and command_group_start_ind < command_match_start_ind2:
                
                # here we have a group
                inner_command_text = '{'
                tag = True
                
        
        if if_str == '\\begin':

            s = re.compile(r'\\begin\{([^\\{}]+)\}')

            env_name = re.findall(s, command)[0]

            if not '\\end{' + env_name + '}' in command:
                
                return f'The following environment does not close: {env_name}', None, None, None
        
        
        if if_str != '\\begin' and tag==False:
            # then we have a normal command 
            
            normal_command_pattern = re.compile(r'\\[^{]*\{') # normal command its pattern

            
            normal_command_ind = re.search(normal_command_pattern, command)
            
            if normal_command_ind is not None:
                
                normal_command_ind = normal_command_ind.start()
                
            else:
                
                normal_command_ind = float('inf')
            
            
            math_command_ind1 = command.find('\\(') # .find() is like .index() but it returns -1 instead of exception when no result found
            
            if math_command_ind1 == -1: # no result found
                
                math_command_ind1 = float('inf')
              
            
            math_command_ind2 = command.find('\\[')
            
            if math_command_ind2 == -1: # no result found
                
                math_command_ind2 = float('inf')
            
            
            math_command_ind3 = command.find('$$')
            
            if math_command_ind3 == -1: # no result found
                
                math_command_ind3 = float('inf')
            
            
            math_command_ind4 = command.find('$')
            
            if math_command_ind4 == -1: # no result found
                
                math_command_ind4 = float('inf')

            command_list_re = [r'\\[\(]', r'\\[\[]', r'\$\$', r'\$', normal_command_pattern]
            ind_list = [math_command_ind1, math_command_ind2, math_command_ind3, math_command_ind4, normal_command_ind]
            smallest_ind = np.argmin(ind_list) # selects the first smallest value


            if smallest_ind == len(command_list_re)-1:
                
                inner_command_text = re.findall(command_list_re[smallest_ind], command)[0]
                
            else:
                
                inner_command_text = re.findall(command_list_re[smallest_ind], command)[0] # first command to find
            # -> inner_command_text is here simply the command opening!

            tag = True # marks in the commandlist_finder that we have a command opening instead of an 
            # environment name!

            
    elif command_match is None:
        
        command_match_group = re.search(r'{', command)
        
        if command_match_group is not None:
            
            command_group_start_ind = command_match_group.start()

            # here we have a group
            inner_command_text = '{'
            tag = True

            
    found_commands_delta, first_begin_ind_delta, last_end_ind_delta, nested_commands_delta = commandlist_finder(command, inner_command_text, tag)
    
    if isinstance(found_commands_delta, str):
        
        return found_commands_delta, None, None, None
    
    _a, center_content_delta, _b = content_creator(found_commands_delta, first_begin_ind_delta, last_end_ind_delta)

    nested_commands_center = nested_commands_delta[first_begin_ind_delta+1 : last_end_ind_delta]

    return center_content_delta, nested_commands_center, found_commands_delta[:first_begin_ind_delta+1], found_commands_delta[last_end_ind_delta:]


# In[27]:


def closed_env_check(string):
    '''
    simply check if there are more closings than openings of environments in the whole string.
    LaTeX Walker is not able to recognize any ending environment command when its beginning is not 
    defined. It is simply ignored totally. Therefore, this function checks for endings without beginnings.
    
    params string -> the string to check
    
    returns:
    boolean -> when True there are as many openings as endings, when False there are more endings than openings
    statement -> describes the environment type for which boolean is False, is None when boolean is True
    '''

    f11 = re.findall(r'\\begin{.*}', string)
    f12 = re.findall(r'\\end{.*}', string)
    
    if len(f11) < len(f12):

        begin_pattern = re.compile(r'\\begin\{([^\\{}]+)\}')
        begin_names = set(re.findall(begin_pattern, string))

        end_pattern = re.compile(r'\\end\{([^\\{}]+)\}')
        end_names = set(re.findall(end_pattern, string))

        non_closing_env_name_list = list(end_names - begin_names)

        if non_closing_env_name_list != []: 
            
             non_closing_env_name = non_closing_env_name_list[0]
                
        else: 
            # should not happen
            
            non_closing_env_name = ''
            
        return False, f'normal environment {non_closing_env_name}'

    
    f21 = re.findall(r'\\\(', string)
    f22 = re.findall(r'\\\)', string)
    
    if len(f21) < len(f22):
        
        return False, 'math environment round brackets'

    
    f31 = re.findall(r'\\\[', string)
    f32 = re.findall(r'\\\]', string)
    
    if len(f31) < len(f32):
        
        return False, 'math environment square brackets'

    
    return True, None


# In[28]:


def prepare_ddmin(raw_string, curr_layer, problem_id):
    ''' 
    only runs for the first time when we start with a given .tex file
    
    params:
    raw_string -> input string which represents the content of the .tex file
    curr_layer -> integer which determines whether a new independent Docker image is created
    problem_id -> integer which descirbes the storage location within an Docker image
    
    returns:
    front_skeleton -> preamble string list
    center_content -> body string list
    back_skeleton -> list with \\end{document} and rest of .tex file
    nested_commands_center -> list over elements/commands of center_content describing whether these are nested
    error_message_stored -> error message of the .tex file (this is used to compare it with the errors
                            produced by modified versions)
    '''
    
    # first check if there is the same number of beginning and ending commands of the environment. Do this
    # because LaTeXWalker simply ignores the ending command (it cancels it) when no beloning beginning 
    # command is given:
    boolean, env_type = closed_env_check(raw_string)
    
    if not boolean:
        
        return f'Error: we end a ' + env_type + ' without beginning it.', None, None, None, None
    
    
    # create .log file with error message:
    log_file_image_path_full_file, container_name, project_folder = docker_organizer(curr_delta=str('beginDelta'),curr_latex_string=raw_string, problem_id=0, first_run=True)
    
    # look for the error within the log file:
    if log_file_image_path_full_file == '':
        
        raise Exception('Input tex file produces no .log file when using pdfLaTeX. Unusual error!')

    error_message_stored = latex_failure_check(log_file_image_path_full_file, container_name, project_folder)
    
    if error_message_stored == '':
        
        return 'Input .tex file has no error message!', None, None, None, None
    
    # parser/find commands:
    found_commands, first_begin_ind, last_end_ind, nested_commands_delta = commandlist_finder(raw_string, start_content_comment='document')
    # found commands: list of commands including all commands of the LaTeX file
    # first_begin_ind and last_end_ind: indices which describe the start and end of the center_content below
    # nested_commands: list which describes for each command if it is nested, important for later split!
    
    if isinstance(found_commands, str):
        
        return found_commands, None, None, None, None
    
    # split the command list into following parts:
    front_skeleton, center_content, back_skeleton = content_creator(found_commands, first_begin_ind, last_end_ind)
    # front_skeleton: list of commands which appear before included '\begin{document}'. This can be 
    # spilt in later process when it contains nested commands!
    # back_skeleton: list of commands which appear after included '\end{document}'
    # center_content: list of commands which are embedded within the document structure and are independent
    # of each other
    
    nested_commands_center = nested_commands_delta[first_begin_ind + 1 : last_end_ind]

    return front_skeleton, center_content, back_skeleton, nested_commands_center, error_message_stored


# In[29]:


def env_content_filter(string, aim_outer_bracket=2, tag='newenv', squared=False): # or 1 # tag: pre, post, command, newenv
    '''
    is the helper function of env_enterer(). It looks at the bracket of an preamble definition to 
    split it into individual commands.
    
    params:
    string -> string of interest, should be of type  \\(re)newenvironment, \\(re)newcommand, \\pre, 
              and \\post
    aim_outer_bracket tags -> integer defining which bracket to target on, \\newenvironment{1}[1]{2}{3}, 
                              \\newcommand{1}[1]{2}, \\pre...{1}, \\post...{1}
    tag -> string which names the type 
    squared -> boolean which states whether there is a [] in the string
    
    returns:
    command_list -> list which contains the single commands/deltas of the bracket content of interest
    nested_commands -> list which determines wheter elements of command_list are nested (True) or not (False)
    front_part -> whole string part in front of the bracket content of interest
    back_part -> whole string part after the bracket content of interest                       
    '''
    
    outer_bracket_counter = 0
    new_outer_command = False
    target_string = ''
    open_bracket_counter = 0
    
    start_ind_content = -1 # mark where the needed enviornment content starts with {
    end_ind_content = 0 # mark where the needed environment content ends with }
    stored_end = -1

    
    if squared:
        
        aim_outer_bracket = 1
        opener = '['
        closer = ']'
        
    else:
        
        opener = '{'
        closer = '}'

        
    for ind_char, char in enumerate(string):
        
        if char == opener:
            
            if open_bracket_counter == 0: # we start a new outer command
                
                new_outer_command = True
                outer_bracket_counter += 1

            else: 
                
                new_outer_command = False

            open_bracket_counter += 1

        elif char == closer:
            
            stored_end = ind_char
            open_bracket_counter -= 1

        else: 
            
            new_outer_command = False     
        
        if open_bracket_counter > 0 and outer_bracket_counter == aim_outer_bracket and new_outer_command==False:

            target_string += char
            
        if outer_bracket_counter == aim_outer_bracket and start_ind_content < 0:
            
            start_ind_content = ind_char
            
        if target_string != '' and open_bracket_counter == 0:

            end_ind_content = stored_end
            break
            
        # -> output: target_string, start_ind_counter, end_ind_counter
    
    # Next get command_list:
    command_list, start_content_ind2, end_content_ind2, nested_commands = commandlist_finder(target_string, start_content_comment='')
    
    if isinstance(command_list, str):
        
        return command_list, None, None, None
    
    front_part = string[:start_ind_content+1] # +1 to include the opening bracket
    back_part = string[end_ind_content:]

    return command_list, nested_commands, front_part, back_part 


# In[30]:


def env_enterer(front_skeleton, center_content, back_skeleton, env_position):
    '''
    can walk into preamble definitions, \\(re)newenvironment, \\(re)newcommand, \\pre, and \\post,
    to detect error location. However, due to the syntax of LaTeX it doesn't modify the code at all. 
    However, it would be possible to somehow memorize or mark the detected position.
    Call it when only one element is placed in the center_content.
    
    params:
    front_skeleton -> represents everything in front of the definition of interest
    center_content -> the definition of interest
    back_skeleton -> represents everything after the definition of interest
    env_position -> integer which desribes the current bracket of interest, it  starts with 1
    
    returns:
    front_skeleton -> to input front_skeleton the definition pre area of interest is added
    center_content -> list containing the commands within the brackets of interest
    back_skeleton ->  to input back_skeleton the definition pre area of interest is added
    front_skeleton_input -> inputted front_skeleton
    center_content_input -> inputted center_content
    back_skeleton_input -> inputted back_skeleton
    env_finished -> boolean telling whether every bracket of the definition was entered
    delta_combi_triangle_list -> boolean list which describes whether the commands of center_content_input
                                 are nested (True) or not (False)
    '''

    if env_position == 1:
        
        s1 = 'one'
        
    elif env_position == 2:
        
        s1 = 'two'    
        
    elif env_position == 3:
        
        s1 = 'three'
        
    elif env_position == 4:
        
        s1 = 'four'
        
    else:
        
        raise Exception("Error in entering env with false position!")

    
    front_skeleton_input = front_skeleton
    center_content_input = center_content
    back_skeleton_input = back_skeleton
    
    # search for new_environment:
    pre_env_pattern = re.compile(r'\\(?:re)?newenvironment{') 
    pre_env_pattern2 = re.compile(r'\\(?:re)?newcommand{') 
    

    # my parser should only generate '\\newenvironment{...}{...}' where it starts with 
    # newenvironment and ends with } and therefore is more easy to handle now
    element = center_content[0]

    found = re.search(pre_env_pattern, element)
    found2 = re.search(pre_env_pattern2, element)
    squared = False
    
    if found is not None:
        
        if env_begins:
            
            front_ind -= 1 # jump one back in the front index because later it will jump 
            # one forwards. We want to stay at this element in the front_skeleton for the 
            # next round as we also have to look at the other bracket conditions (the ends)
            # of the environment.
            env_begins = False

        else:
            
            env_begins = True

        tag = 'newenv'
        total_env_position = 3

        
    elif found2 is not None:
        
        tag = 'command'
        total_env_position = 2
        

    elif '\\pre' in element:
        
        tag = 'pre'
        total_env_position = 1
        

    elif '\\post' in element:
        
        tag = 'post'
        total_env_position = 1
    
    
    else:
        
        return None, None, None, None, None, None, None, None

    total_env_position_pattern = re.compile(r'\[.*\]\{') 
    total_env_position_part = re.search(total_env_position_pattern, element)

    
    if (env_position == 1 and total_env_position_part is not None) or not squared:
        
        # the square bracket is counted as env_position but treated extra
        aim_outer_bracket = env_position 
    
    
    if total_env_position_part is not None:
        
        total_env_position += 1
        
        if env_position == 2:
            
            squared = True
            aim_outer_bracket = 1
            
        elif env_position > 2:
            
            aim_outer_bracket = env_position - 1

            
    if total_env_position == env_position:
        
        env_finished = True
        
    else:
        
        env_finished = False
    
    if env_position > total_env_position:
        
        raise Exception("Error in entering env with false position!")
        

    command_list, nest, front_part, back_part = env_content_filter(element, aim_outer_bracket, tag, squared)
    
    if isinstance(command_list, str):
        
        return command_list, None, None, None, None, None, None, None
        
    # create new skeleton by using inner found parts as center_content, add to front_skeleton start of
    # environemnt, add to back_skeleton the closing bracket of the curcial center part:
    front_skeleton = front_skeleton_input.copy()
    back_skeleton = back_skeleton_input.copy()

    
    front_skeleton.append(front_part)
    center_content = command_list
    back_skeleton.insert(0, back_part)

    delta_combi_triangle_list = ['E'+s1+str(i) for i in range(len(center_content))]
    
    # return also original skeleton to use it later for later bracket again:
    return front_skeleton, center_content, back_skeleton, front_skeleton_input, center_content_input, back_skeleton_input, env_finished, delta_combi_triangle_list


# In[31]:


def ddmin(front_skeleton, center_content, back_skeleton, error_message_stored, curr_layer, problem_id, delta_ids=None):
    '''
    implements the ddmin algorithm.
    All possible cases to consider:
    
    a) there is at least one triangle upwards (delta test) which produces a failing test
    b) there is at least one triangle downwards (big_failing_set_c-one trinalge upwards; complements) which produces a failing test
    c) number of current triangle upwards (delta tests) is smaller than the length of the big failing set c (which consists of delta tests and the complements)
    d) reaching an end when no of the cases above happens
    
    -> However, only a) is of interest. The reason lies in the syntax of LaTeX. When we define (cluster of)
       commands as deltas, the error is always located in one of those. So, a) always happens to be the case.
       The algorithm looks first at the body. When the error isn't located there, the ddmin is executed
       again on the preamble/front skeleton of the .tex file. Code after the body is ignored by pdfLaTeX.
       So, there is no need in b) formulating complements. c) is implemented indirectly: When we find 
       a nested delta it is split up into individual, smaller deltas which are all tested individually. 
       This happens to be the case in ddmin_loop(). d) happens automatically the case when a) and c) aren't
       activated any longer. Then we return the last delta embedded in the minimalistic LaTeX structure 
       which threw the error which is identical with one of the originally inputter .tex file. 
       
    params: 
    front_skeleton -> preamble/front of the area of interest/center_content
    center_content -> list of commmands/deltas to work with ddmin
    back_skeleton -> part after area of interest/center_content
    error_message_stored -> the error message of the original .tex file which we aim for
    curr_layer -> interger for creating a new, independent Docker image
    problem_id -> the storage place of the generated .log files of pdfLaTeX within the current Docker image
    delta_ids -> list which enumerates the deltas/elements of center_content
    
    returns:
    center_content_triangle -> the current delta (combination) of interest which leads to error
    delta_id_list -> the current enumeration for the center_content_triangle
    statement -> 'error for the given delta'
    '''

    center_content_full = center_content
    
    # fix the index list such that the deltas which are named after the indices of the central skeleton body, 
    # can't change:
    if len(front_skeleton) > 0:
        
        delta_id_list = [str(i) for i in range(0, len(center_content))]
        p_str = ''
        
    else:
        # we assume that the current deltas are the preamble itself. Therefore we mark them with 'P'
        # for preamble
        delta_id_list = ['P'+str(i) for i in range(0, len(center_content))]
        p_str = 'P'
    
    # ddmin:
    # frist step: spit center_content into two parts
    # go through each triangle, but stop with that when one triangle throws the same error message as the 
    # stored error message from the whole file:
    triangle_delta_combi_history = {}
    final_error = ''
    
    env_entered = False 
    env_finished = False
        
        
    while True:
        
        broken = False
        
        divider = 2
        divider_multiplier = 1
        biggest_ind = 0        
        
        ''' 
        multi-processing idea:
        run several pdfLaTeX processes in parallel to save time. 
        
        from multiprocessing import Process
        
        def errorSearchFunctionCombiner(args....):
        
            a = docker_organizer(...)
            error_message = latex_failure_check(a)
            return error_message
        
        def parallelErrorSearch(*triangles_info):
        
            proc = []
            
            for triangle_info in triangles_info:
            
                p = Process(target=errorSearchFunctionCombiner, args=(triangle_info,))
                p.start()
                proc.append(p)
                
            for p in proc:
            
                p.join()
        
        '''

        
        first_run = True
        last_run = False

        # loop over the center content, cut it into deltas and test them:
        while biggest_ind < len(center_content) or not last_run: # go over all triangles

            smallest_ind = biggest_ind # the previous biggest_ind
            
            # first time we start this loop, we check the blank body, after that we check for the 
            # center parts (deltas) which result from a split:
            if biggest_ind >= len(center_content):
                
                smallest_ind = 0
                biggest_ind = 0
                last_run = True

            else:

                biggest_ind = divider_multiplier * (max(len(center_content) // divider, 1)) 
                divider_multiplier += 1
              
            
            if biggest_ind >= len(center_content):
                    
                center_content_triangle = center_content[smallest_ind:]   
                delta_combi_triangle_list = delta_id_list[smallest_ind:]

            else:

                center_content_triangle = center_content[smallest_ind : biggest_ind]  
                delta_combi_triangle_list = delta_id_list[smallest_ind : biggest_ind]

                
            # bring active center part to one string:
            delta_combi_triangle = ''.join(delta_combi_triangle_list)
            
            if delta_combi_triangle == '':
                
                delta_combi_triangle = p_str + 'blankBody'
                
            # When this delta was already used, go to next center part to try out in this while loop:
            if delta_combi_triangle in triangle_delta_combi_history.keys():
                
                continue # the rest round of this inner while loop can be ignored, jump to next triangle

            # add active center (deltas) to history, to avoid second check:
            triangle_delta_combi_history[delta_combi_triangle] = center_content_triangle
            

            # build whole LaTeX string to check on with current center content:
            triangle = ''.join(front_skeleton + center_content_triangle + back_skeleton)
            

            '''
            for multi-processing we would collect all the info from the loop above in lists and leave the 
            loop now. The following code would be executed in parallel for all triangles to search for the 
            error in parallel. When we found the error we should take a triangle for which it is happening
            to further work with in the ddmin function. The rest shall be ignored.
            
            same can be done for complements.
            '''
            
            # try to create pdf via pdflatex and check it for failures:

            log_file_image_path, container_name, project_folder = docker_organizer(curr_delta=delta_combi_triangle, curr_latex_string=triangle, problem_id=problem_id)
            # look for the error within the log file:
            if log_file_image_path == '':
                # no log file generated
                
                break
                
            error_message = latex_failure_check(log_file_image_path, container_name, project_folder)

            # error still there, so error in the current delta, split it again into two to find precise
            # error position. Enter this loop again with the current center content as the new center 
            # content to split:

            if error_message == error_message_stored: # case a) reduce to subset

                # when we have a blank body file but still the same error, ddmin is returns with the 
                # message that error outside body:
                if len(center_content_triangle) == 0:

                    # when we have a center of [] but still get an error then the error has to be in
                    # the front or back skeleton.

                    if env_finished:
                        # modify center_content to whole environment as we have here a blank body and the 
                        # error was produced by full env:
                        
                        center_content_triangle = ''.join(front_skeleton2) + ''.join(center_content_before_break) + ''.join(back_skeleton2)

                        delta_combi_triangle_list = ['']

                        return center_content_triangle, delta_combi_triangle_list, 'error after environment run'
                    
                    return center_content_triangle, delta_combi_triangle_list, 'error outside skeleton center'
                    # returns failing list
                    
                    
                # When we are finished with testing env and still the same error happens, we set back the
                # front and back skeleton such that they don't contain environment splitters:
                if env_entered and env_finished and biggest_ind >= len(center_content)-1:
                    front_skeleton = front_skeleton_input
                    back_skeleton = back_skeleton_input
                    
                if ((len(center_content_triangle) == 1 and not env_entered) or (env_entered and biggest_ind >= len(center_content)-1)) and env_finished == False: # d3.4

                    # check if environment enterer was already entered:
                    if env_entered:
                        
                        env_position += 1
                        front_in = front_skeleton_input
                        center_in = center_content_input
                        back_in = back_skeleton_input
                        
                    else:
                        
                        env_position = 1
                        front_in = front_skeleton 
                        center_in = center_content_triangle
                        back_in = back_skeleton
                        
                    front_skeleton2, center_content_triangle2, back_skeleton2, front_skeleton_input, center_content_input, back_skeleton_input, env_finished, delta_combi_triangle_list2 = env_enterer(front_in, center_in, back_in, env_position)

                    if isinstance(front_skeleton2, str):

                        return front_skeleton2, None, None

                    elif front_skeleton2 is None:
                        
                        pass
                    
                    else:

                        front_skeleton = front_skeleton2
                        center_content_triangle = center_content_triangle2
                        back_skeleton = back_skeleton2

                        delta_combi_triangle_list = delta_combi_triangle_list2
                        env_entered = True

                        center_content_before_break = center_content_triangle2

                # Happens always when error the same as original error:
                center_content = center_content_triangle

                delta_id_list = delta_combi_triangle_list
                divider = 2
                divider_multiplier = 1
                biggest_ind = 0
                # divider, biggest_ind, and dividider_multiplier are already intitalized correctly at beginning
                # of while loop.   
                
                broken = True
                break
                
            elif error_message != error_message_stored and len(center_content_triangle) == 0:
                # in the previous round we had the center content of length 1 with a failing delta,
                # center_content=[failing_delta]. We split it up into center content parts to loop over,
                # [] and [failing_delta]. 
                # Now we treat the [] when we don't get the searched error for it when we use it as 
                # center content then the problem lies in the failing_delta and not in the front or back
                # skeleton. 
                # When the delta is a nested command then we will split it up further to localize the 
                # error more precisely. When it is not nested, we are done. 
                
                if env_finished:
                    # modify center_content to whole environment as we have here a blank body and the 
                    # error was produced by full env:
                    center_content[0] = front_skeleton2[-1] + center_content[0] + back_skeleton2[0]

                return center_content, delta_id_list, 'error for the given delta'
                # return the previous center content [failing_delta] and delta_id_list.
                # returns failing list.      


# In[32]:


img_counter = 0
img_str = ''

def docker_organizer(curr_delta, curr_latex_string, problem_id=0, first_run=False):
    '''
    creates Dockerfiles, creates Docker image, and runs pdfLaTeX within Docker image to store the resulting
    .log file within that Docker image.
    
    Docker file: file which contains instructions about installations and processes
    Image: compiled Docker file. 
    Container: instance of an image, is the virtual operating system.
      
    params:
    curr_delta -> the active delta enumeration. It is taken to formulate a name for the created .log file
    curr_latex_string -> string which contains the whole code to convert by pdfLaTeX
    problem_id -> defines the storage location of the pdfLaTeX outcome files
    first_run -> boolean when True new, independent image is built, else the current images relies on the 
                 independent image
    
    returns:
    log_file_image_path -> the path where the .log file is stored within the Docker image
    container_name -> the name of the Docker container which is an instance of the current Docker image
    project_folder -> the folder which is the working directory of the created Docker image and which will
                      also be used as the host location in latex_failure_check()   
    '''
    print('######################################################')
    print('docker_organizer(): Convert following string with pdfLaTeX:\n', curr_latex_string)

    container_name =  f'latex_container_{int(time.time())}' 
    project_folder = 'project_folder'
    global img_counter
    global img_str

    if first_run:
        # create the folders when running for a .tex file the first time at all
        
        if os.path.exists(project_folder):
            
            shutil.rmtree(project_folder)

        os.makedirs(project_folder, exist_ok=True)
        
        img_counter = 0
        img_str = ''
    
        curr_image_title = 'ubuntu:latest'# 'ubuntu:18.04'   
        
    elif img_counter % (31 - 7) == 0: 
        # in Docker the maximal depth can be exceeded. Therefore, create new, independent Docker image.
        
        first_run = True
        img_str = str(img_counter) # modify img_str such that new image type can be created
            
        curr_image_title = 'imagename' + img_str 
        
    else:
        
        curr_image_title = 'imagename' + img_str 
                            
    img_counter += 1
    
    os.makedirs(project_folder + '/' + curr_delta, exist_ok=True)

    
    with open(f'{project_folder}/{curr_delta}/{curr_delta}.tex', 'w') as g:
        g.write(curr_latex_string)

    # Docker File:
    with open(f'{project_folder}/{curr_delta}Dockerfile', 'w') as f:
        
        # write header with current image title:
        f.write(f'FROM ubuntu:latest \n\n')
        #f.write(f'FROM ubuntu:18.04 \n\n') # this Docker file refers to image with the name ubuntu:18.04
        # such that there is no need of installation of TeX every time

        f.write(f'RUN apt-get update && apt-get install -y texlive \n')
        # the texlive package also contains pdfLaTeX

        # use RUN to execute the commands from inside of container:
        if first_run: 

            f.write(f'RUN mkdir /home/{project_folder} && \ \n')
            f.write(f'mkdir /home/{project_folder}/{str(problem_id)}{str(problem_id)} \n')
        
        f.write(f'WORKDIR /home/{project_folder} \n') # set working directory
        
        # copy the local .tex file on host to the image:
        f.write(f'COPY ./{curr_delta}/{curr_delta}.tex ./{str(problem_id)}{str(problem_id)} \n')
        # the .tex file to copy has to be placed in the cwd directory of the Docker build command. 

        # create the .pdf file:
        f.write(f'RUN pdflatex -interaction=nonstopmode -output-directory ./{str(problem_id)}{str(problem_id)} ./{str(problem_id)}{str(problem_id)}/{curr_delta}.tex 2>&1 | tee ./{str(problem_id)}{str(problem_id)}/{curr_delta}.log \n  ')
        # 2>&1 | tee ./00/begin2.log to run the command even when an error appears, through that we can generate the .log file which points out the searched error

    # collect log file paths:
    log_file_image_path = f'/home/{project_folder}/{str(problem_id)}{str(problem_id)}/{curr_delta}.log'

    if not first_run:
        # remove unused images
        
        command_docker = 'docker image prune --force'
        subprocess.run(command_docker, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    
    # build inital image (lower directory; read only):
    subprocess.run(['docker', 'build', '-t', curr_image_title, '-f', f'{project_folder}/{curr_delta}Dockerfile', f'{project_folder}'])
    # builds a new image layer based on existing base image (overlay file system)
        
    # create Docker container:
    subprocess.run(['docker', 'run', '-it','--name', container_name, '-p', '0:80', '-d', curr_image_title])
    # port 0: A random free port from 1024 to 65535 will be selected. 
    # A port in computer software is when a piece of software has been translated or converted to run 
    # on different hardware or operating system (OS) than it was originally designed for.
    # the container is only an instance of an image.

    subprocess.run(['docker', 'run', '-v',  f'{os.path.abspath("")}/{project_folder}:/home/{project_folder}', curr_image_title])

    return log_file_image_path, container_name, project_folder


# In[33]:


def ddmin_connected(file_name):
    '''
    is called by the user to start the process.
    
    params:
    file_name -> the path including the .tex file to process
    user -> the logged-in user of the current computer
    password -> the password for the user to give permission for initial Docker runs
    
    returns:
    ddmin_loop() -> function call to go to the next process step
    '''
    
    # open the file as string:
    raw_string = open_full_file_as_string(file_name=file_name)
    
    front_skeleton, center_content, back_skeleton, nested_commands_center, error_message_stored = prepare_ddmin(raw_string, curr_layer=0, problem_id=0)
    
    if isinstance(front_skeleton, str):
        
        return front_skeleton
    
    first_front_skeleton = front_skeleton
    first_back_skeleton = back_skeleton

    if center_content == []:
        # as described above the \begin{document} AND/OR maybe \end{document} are missing.
        
        return 'The \\begin{document} and/or \\end{document} are missing!'

    return ddmin_loop(front_skeleton, center_content, back_skeleton, nested_commands_center, error_message_stored, first_front_skeleton, first_back_skeleton)
    
def ddmin_loop(front_skeleton, center_content, back_skeleton, nested_commands_center, error_message_stored, first_front_skeleton, first_back_skeleton):
    '''
    organizes the process by running the ddmin() algorithm and reacting to its output statement.
    
    params:
    front_skeleton -> preamble/front skeleton in front of the center of interest/center_content
    center_content -> list with current deltas of interest, body or content of nested command
    back_skeleton -> back skeleton after the center of interest/center_content
    nested_commands_center -> list refering to the elements/deltas of center_content informing whether the
                              deltas are nested (True) or not (False)
    error_message_stored -> the error message produced by the original .tex file which we target on
    first_front_skeleton -> unmodified front skeleton to perceive the valid .tex structure
    first_back_skeleton -> unmodified back skeleton to perceive the valid .tex structure
    
    returns final_latex -> the final LaTeX code output presented as a string, concretizing the error 
                           location
    '''
    
    first_time_outside = True
    looper = True
    env_begins = True # mark if we want the {begins} or the {ends} of the newenvironment
    front_ind = 0
    
    while True:

        center_content, delta_id_list, statement = ddmin(front_skeleton, center_content, back_skeleton, error_message_stored, curr_layer=1, problem_id=0)

        if isinstance(center_content, str):
            
            return center_content
        
        if statement == 'error outside skeleton center':
            # we have to split the front (and back) skeleton until the error doesn't appear anymore.
            # the returned center_content is [] with delta_id_list=[], therefore we can ignore it and
            # build up a new skeleton!
            
            # when the error is outside the skeleton, transfer all the front skeleton commands to the 
            # center:
            if first_time_outside:
                # the first time we find out that the error has to be beyond the center_content 

                center_content = []
                nested_commands_center = []
                f1 = []

                for command in front_skeleton:
                    
                    command_list, start_content_ind, end_content_ind, nested_commands_delta = commandlist_finder(command, '')

                    if isinstance(command_list, str):
                        
                        return command_list
                    
                    for c_ind, command in enumerate(command_list):
                        
                        if '\\documentclass' in command or f1 == []:
                            # all commands before \\documentclass get stored in front skeleton
                            
                            if f1 == [] and (not command.startswith('%') and not '\\documentclass' in command):
                                
                                return 'Final output: command before \\documentclass or \\documentclass missing/mis-spelled.'
                            
                            f1.append(command)
                            
                        elif '\\begin{document}' in command:
                            
                            back_skeleton.insert(0, command)
                            
                        else:
                            
                            center_content.append(command)
                            nested_commands_center.append(nested_commands_delta[c_ind])

                            
                front_skeleton = f1
                first_time_outside = False
                
            
            else: # second time outside
                # error has to lay in \\documentclass, \\begin{document}, or \\end{document}

                if first_front_skeleton[-1] != '\\begin{document}' or first_back_skeleton[0] != '\\end{document}':

                    return first_front_skeleton[-1] + first_back_skeleton[0]
                
                else: # we have error in \\documentclass, e. g. spelling error in it:

                    for command in first_front_skeleton:
                        # we already know that only comments can stand in front of documentclass, else 
                        # we would have returned earlier l. 57 this box.
                        
                        if not command.startswith('%'):
                            
                            return command
                                  
                    
        elif statement == 'error after environment run':
            
            final_latex = ''.join(center_content)
            return final_latex
                    
        elif statement == 'error for the given delta':
            # we have to check whether the given delta can be split up in further parts. 
            # according to the algorithm the returned center_content only contains one element, the failing 
            # delta. This fits to the assumptions about the syntax of latex.
            
            # Here we assume that the returned center_content contains several elements:
            # consider case that used deltas can be nested deltas. Further spilt them up:
            copy_delta_id = []
            
            for ele in delta_id_list:
                
                copy_delta_id.append(re.sub(r'[A-Za-z]','',ele))
            
            active_nests = np.array(nested_commands_center, dtype=bool)[np.array(copy_delta_id, dtype=int)]


            if True in active_nests: # also seen as nest '\\begin{qoute}\ntext\n\\end{quote}\n'
                
                if center_content == []: # so the commandlist_finder realized a \\begin{a} but we dont
                    # have a \\end{a}
                    
                    final_latex = ''.join(front_skeleton + center_content_old + back_skeleton)   
                    return final_latex   
                
                commands_to_split = list(np.array(center_content)[np.where(active_nests==True)])

                new_center_list = []
                new_nested_commands_center = []

                for ind_command, single_command in enumerate(commands_to_split):
                    # when everything is right this loop should only last one round because commands_to_split
                    # should have only one element

                    center_content_delta, nested_commands_center, command_forth, command_back = delta_splitter(single_command)

                    if isinstance(center_content_delta, str):
                        
                        return center_content_delta
                    
                    # new center body of skeleton is formed by removing nested structure of list:
                    new_center_list.extend(center_content_delta)
                    new_nested_commands_center.extend(nested_commands_center)
                    
                    ############################################
                    '''
                    At this point we found out that the error has to lay in one of the nested commands.
                    When everything is right, we should only have one nest/single_command which contains
                    the error
                    
                    Three types of error are possible:
                    
                    a) Content error: one delta in nest leads to the error 
                        -> Test every delta without nest, one has to lead to error
                        -> ddmin with aim 'error for given delta', avoid 'error outside center'
                    
                    b) Shell error: the nest itself contains the error 
                        -> Test empty shell
                        -> One run using empty shell in creating pdf; compare the test to the environement
                           run with the WHOLE content to be sure that the change of error relies on the 
                           current nest and not an other nest
                    
                    c) Content-shell interaction error: Only in the combination of delta in the nest error 
                        -> Test every delta with surrounding nest, when same error we have c) fulfilled given
                           a) and b) first tested
                        -> ddmin with aim 'error for given delta', avoid 'error outside center'; input
                           is the shell in front and back skeleton and the whole content of shell as center
                    
                    d) Content-shell interaction error: like c) but not one delta content enough, several
                       content parts needs to be used to cause exactly the searched error:
                       -> When going in nest from delta to delta add each time one content element more
                          until error appears
                    '''
                    
                    # b):
                    command_ele_front = ''.join(command_forth) #'\\begin{' + command_ele + '}'
                    command_ele_back = ''.join(command_back) #'\\end{' + command_ele + '}'
                    
                    # test empty shell of nest:                       
                    latex_string_inter = ''.join(front_skeleton + [command_ele_front] + [command_ele_back] + back_skeleton)  
                    curr_delta_inter = f'emptyShell{ind_command}'
                    log_file_image_path_inter, container_name_inter, project_folder_inter = docker_organizer(curr_delta=curr_delta_inter,curr_latex_string=latex_string_inter, first_run=False)
                    error_message_inter = latex_failure_check(log_file_image_path_inter, container_name_inter, project_folder_inter)

                    if error_message_inter == error_message_stored:
                        # error lies in the empty shell
                        
                        return latex_string_inter


                    # a): Test if single command error, then if nested to put in ddmin_looper
                    # c): Works like a) but with slightly modified front and back skeleton
                    # d): works like c) but extends center
                    d_counter = 0
                    c_list = []
                    
                    for f, b in [('',''),(command_ele_front, command_ele_back),(command_ele_front, command_ele_back)]:
                        
                        d_counter += 1
                        
                        for d, c in zip(nested_commands_center, center_content_delta):
                            
                            if d_counter == 3:
                                
                                c_list.append(c)
                                c_cur_list = c_list
                                
                            else:
                                
                                c_cur_list = [c]

                            # test single command for error:
                            latex_string_inter = ''.join(front_skeleton + [f] + c_cur_list + [b] + back_skeleton) 
                            curr_delta_inter = f'nestContentOnly{ind_command}{d}'
                            
                            log_file_image_path_inter, container_name_inter, project_folder_inter = docker_organizer(curr_delta=curr_delta_inter,curr_latex_string=latex_string_inter, first_run=False)
                            error_message_inter = latex_failure_check(log_file_image_path_inter, container_name_inter, project_folder_inter)

                            if error_message_inter == error_message_stored:
                                # in this command lays error

                                command_list_d, start_content_ind_d, end_content_ind_d, nested_commands_d = commandlist_finder(c, start_content_comment='')

                                if isinstance(command_list_d, str):
                                    
                                    return command_list_d
                                
                                if True in nested_commands_d:
                                    # The current command contains the error and can be split up further
                                    # -> put it into ddmin_looper
                                    
                                    front_skeleton = front_skeleton + [f]
                                    back_skeleton = [b] + back_skeleton 

                                    return ddmin_loop(front_skeleton, command_list_d, back_skeleton, nested_commands_d, error_message_stored, first_front_skeleton, first_back_skeleton)
                                
                                else:

                                    # error in c but it is not nested
                                    return latex_string_inter

                        
                    # error lies in the full command but not determinable where exactly, therefore
                    # return command with 
                    print('ERROR NOT FOUND')
                    return None
                    
                    ############################################

                    
            else:

                # when we have a front skeleton of len 0 all its content is stored in the center
                if len(front_skeleton)>0:
                    
                    final_latex = ''.join(front_skeleton + center_content + back_skeleton)   
                    return final_latex   


# In[34]:


path_input = input('Define .tex file name or path, e. g. tex_test_files/incorrect1.tex')

if path_input == '':
    
    path_input = 'tex_test_files/incorrect1.tex'
    
elif '/' not in path_input:
    # we only have the filename 
    
    if '.tex' not in path_input: 
        # we only have the filename without extension
        
        path_input = 'tex_test_files/' + path_input  + '.tex'
    
    else:
        
        path_input = 'tex_test_files/' + path_input 
    
final_latex = ddmin_connected(file_name=path_input)


# In[35]:


print(final_latex)


# Done
