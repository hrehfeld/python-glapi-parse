import xml.etree.ElementTree as ET

import glob
import sys

class FunctionParameter:
    def __init__(self, name, type):
        self.name = name
        self.type = type

    def __repr__(self):
        return self.type + ' ' + self.name

class FunctionPrototype:
    def __init__(self, name, return_type, parameters):
        self.name = name
        self.return_type = return_type
        self.parameters = parameters

    def transform_parameters(self):
        class TransformNotPossible(Exception):
            pass
        class OptionalNotFound(Exception):
            pass
            
        def eq(s):
            def f(name):
                return name == s
            return f

        class OneofPrefixSamePostfix:
            def __init__(self, prefixes):
                self.prefixes = prefixes
                self.num_called = 0
                self.postfix = None
                
            def __call__(self, pname):
                prefix = self.prefixes[self.num_called]
                self.num_called += 1

                if pname.find(prefix) != 0:
                    return False

                rest = pname[len(prefix):]
                if self.postfix is None:
                    self.postfix = rest
                else:
                    if len(rest) != len(self.postfix) or rest.find(self.postfix) != 0:
                        return False
                        
                return True

        class OneofWithSameRest:
            def __init__(self, fixes, postfixes = False):
                self.fixes = fixes
                self.num_called = 0
                self.rest = None
                self.postfixes = postfixes
                if postfixes:
                    self.get_fix_start = str.rfind
                    self.get_supposed_fix_start = lambda pname, fix: len(pname) - len(fix)
                else:
                    self.get_fix_start = str.find
                    self.get_supposed_fix_start = lambda a,b: 0
                
            def __call__(self, pname):
                fix = self.fixes[self.num_called]
                self.num_called += 1
                
                fix_start = self.get_fix_start(pname, fix)
                if fix_start != self.get_supposed_fix_start(pname, fix):
                    return False
                    

                rest = pname[:fix_start] if fix_start > 0 else pname[len(fix):]
                if self.rest is None:
                    self.rest = rest
                else:
                    if len(rest) != len(self.rest) or rest.find(self.rest) != 0:
                        return False
                        
                return True

        class TransformParameter:
            def __init__(self, is_valid_name, types, required = True):
                self.is_valid_name = is_valid_name
                self.types = types
                self.required = required
        class Transform:
            def __init__(self, parameters, getReplacement):
                self.parameters = parameters
                self.getReplacement = getReplacement

            def reset(self): 
                pass

            def transform(self, parameters):
                self.reset()
                try:
                    numValid = 0
                    try:
                        for j in range(0, len(self.parameters)):
                            t = self.parameters[j]
    
                            e = OptionalNotFound()
                            if t.required:
                                e = TransformNotPossible()
                            def onError():
                                raise e
                                
                            if j >= len(parameters):
                                onError()
                            p = parameters[j]
                            if not t.is_valid_name(p.name) or p.type not in t.types:
                                onError()
                            numValid += 1
    
                    except OptionalNotFound:
                        pass
                    return numValid
                except TransformNotPossible as e:
                    sys.stderr.write(str(e))
                    return 0

        class FixSetTransform(Transform):
            def __init__(self, prefixes, arepostfixes, numRequired):
                self.checker = OneofWithSameRest(prefixes, arepostfixes)

                parameters = []
                for i in range(len(prefixes)):
                    parameters.append(TransformParameter(self.checker, size_types, i < numRequired))
                Transform.__init__(self, parameters
                                   , lambda numValid: FunctionParameter(self.checker.rest if len(self.checker.rest) else 'position'
                                                                        , '::glm::ivec' + str(numValid)))

            def reset(self):
                self.checker.num_called = 0


        size_types = ['GLsizei', 'GLint', 'int', 'size_t', 'unsigned']

                     
        transforms = [#Transform([   TransformParameter(eq('width') , size_types)
                      #              , TransformParameter(eq('height'), size_types)
                      #              , TransformParameter(eq('depth') , size_types, False)
                      #          ]
                      #          , lambda numValid: FunctionParameter('size', '::glm::ivec' + str(numValid))
                      #      )



                      FixSetTransform(['width', 'height', 'depth'], True, 2)
                      , FixSetTransform(['Width', 'Height', 'Depth'], True, 2)
                      , FixSetTransform(['x', 'y', 'z', 'w'], True, 2)
                      , FixSetTransform(['X', 'Y', 'Z', 'W'], True, 2)
                      #FixSetTransform(['x', 'y', 'z', 'w'], False, 2)
                      ]

        parameters = self.parameters
        print('---' + str(self))
        changed = False
        for transform in transforms:
            transformed = []
            i = 0
            while i < len(parameters):
                numValid = transform.transform(parameters[i:])
                if numValid > 0:
                    transformed.append(transform.getReplacement(numValid))
                    changed = True
                    i += numValid - 1
                    print(parameters)
                    
                else:
                    transformed.append(parameters[i])  
                i += 1
            parameters = transformed

        r = FunctionPrototype(self.name, self.return_type, parameters)
        if changed:
            print(r)
        return r


    def __repr__(self):
        return self.return_type + ' ' + self.name + '(' + ', '.join([str(p) for p in self.parameters]) + ')'

def parse_file(filename):
    tree = ET.parse(filename)
    root = tree.getroot()

    func_prototypes = root.iter('funcprototype')
    func_prototypes = [parse_func_prototype(f) for f in func_prototypes]
    return func_prototypes

def parse_func_prototype(func_node):
    params = []

    for pdef in func_node.findall('paramdef'):
        ps = pdef.findall('parameter')
        if len(ps) < 1:
            continue
        assert(len(ps) == 1)
        type_ = pdef.text.strip()
        assert(type_ is not None)
        p = FunctionParameter(ps[0].text.strip(), type_)
        params.append(p)

    fdefs = func_node.findall('funcdef')
    assert(len(fdefs) == 1)
    fdef = fdefs[0]
    functions = fdef.findall('function')
    assert(len(functions) == 1)
    f = FunctionPrototype(functions[0].text.strip(), fdef.text.strip(), params)
    return f




        
    
            
#files = glob.glob('man4/glInva*.xml');
files = glob.glob('man4/glCopyImageSub*.xml');

files = files[:300]

funcs = []

for filename in files:
    try:
        r = parse_file(filename)
        funcs += r
    except:
        sys.stderr.write("Couldn't parse " + filename + '\n')


funcs = [f.transform_parameters() for f in funcs]


class_start = '''#ifndef GL_GLFUNCTIONS_HPP
#define GL_GLFUNCTIONS_HPP

namespace gl
{
	class GlFunctions
	{
	public:
'''

class_end = '''
	};
} // namespace gl

#endif // GL_GLFUNCTIONS_HPP
'''

#print(class_start)
#for f in funcs:
#    print('		' + str(f) + ';')
#print(class_end)

