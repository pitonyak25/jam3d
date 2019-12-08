#!/usr/bin/env python
import sys,os
import time
import numpy as np

#--from qcdlib
import qcdlib
from   qcdlib import pdf0,ff0,pdf1,ff1
import qcdlib.aux
import qcdlib.alphaS
import qcdlib.interpolator

#--from obslib
import obslib.sidis.residuals
import obslib.sidis.reader
import obslib.sia.collins0
import obslib.sia.residuals
import obslib.sia.reader
import obslib.moments.reader
import obslib.moments.residuals
import obslib.AN_pp.AN_theory0
import obslib.AN_pp.residuals
import obslib.AN_pp.reader

#--from fitlib
from fitlib.parman import PARMAN

#--from tools 
from tools.tools    import checkdir
from tools.config   import conf,load_config
from tools.parallel import PARALLEL

class RESMAN:

    def __init__(self,nworkers=2,parallel=True,datasets=True):

        self.setup_core()
        self.parman=PARMAN()
        if datasets:

            if 'sidis'   in conf['datasets']: self.setup_sidis()
            if 'sia'     in conf['datasets']: self.setup_sia()
            if 'moments' in conf['datasets']: self.setup_moments()
            if 'AN'      in conf['datasets']: self.setup_AN()

        if  parallel:
            self.setup_parallel(nworkers)
            self.requests=self.get_requests()
   
    def setup_core(self):

        conf['aux'] = qcdlib.aux.AUX()

        if 'pdf'          in conf['params']: conf['pdf']          = pdf0.PDF()
        if 'transversity' in conf['params']: conf['transversity'] = pdf1.PDF()
        if 'sivers'       in conf['params']: conf['sivers']       = pdf1.PDF()
        if 'boermulders'  in conf['params']: conf['boermulders']  = pdf1.PDF()
        if 'ffpi'         in conf['params']: conf['ffpi']         = ff0.FF('pi')
        if 'ffk'          in conf['params']: conf['ffk']          = ff0.FF('k')
        if 'collinspi'    in conf['params']: conf['collinspi']    = ff1.FF('pi')
        if 'collinsk'     in conf['params']: conf['collinsk']     = ff1.FF('k')
        if 'Htildepi'     in conf['params']: conf['Htildepi']     = ff1.FF('pi')
        if 'Htildek'      in conf['params']: conf['Htildek']      = ff1.FF('k')

    def setup_sidis(self):
        conf['sidis tabs']    = obslib.sidis.reader.READER().load_data_sets('sidis')
        self.sidisres = obslib.sidis.residuals.RESIDUALS()

    def setup_sia(self):
        conf['sia tabs']    = obslib.sia.reader.READER().load_data_sets('sia')
        self.siares = obslib.sia.residuals.RESIDUALS()

    def setup_AN(self):
        conf['AN tabs']   = obslib.AN_pp.reader.READER().load_data_sets('AN')
        self.ANres = obslib.AN_pp.residuals.RESIDUALS()

    def setup_parallel(self,nworkers):
        self.parallel=PARALLEL()
        self.parallel.task=self.task
        self.parallel.set_state=self.set_state
        self.parallel.setup_master()
        self.parallel.setup_workers(nworkers)
        self.nworkers=nworkers

    def get_state(self):
        state={}
        if 'pdf'          in conf: state['pdf'         ]    = conf['pdf'          ].get_state()
        if 'transversity' in conf: state['transversity']    = conf['transversity' ].get_state()
        if 'sivers'       in conf: state['sivers'      ]    = conf['sivers'       ].get_state()
        if 'boermulders'  in conf: state['boermulders' ]    = conf['boermulders'  ].get_state()
        if 'ffpi'         in conf: state['ffpi'        ]    = conf['ffpi'         ].get_state()
        if 'ffk'          in conf: state['ffk'         ]    = conf['ffk'          ].get_state()
        if 'collinspi'    in conf: state['collinspi'   ]    = conf['collinspi'    ].get_state()
        if 'collinsk'     in conf: state['collinsk'    ]    = conf['collinsk'     ].get_state()
        if 'Htildepi'     in conf: state['Htildepi'    ]    = conf['Htildepi'     ].get_state()
        if 'Htildek'      in conf: state['Htildek'     ]    = conf['Htildek'      ].get_state()
        return state

    def set_state(self,state):
        if 'pdf'          in conf: conf['pdf'         ].set_state(state['pdf'         ])
        if 'transversity' in conf: conf['transversity'].set_state(state['transversity'])
        if 'sivers'       in conf: conf['sivers'      ].set_state(state['sivers'      ])
        if 'boermulders'  in conf: conf['boermulders' ].set_state(state['boermulders' ])
        if 'ffpi'         in conf: conf['ffpi'        ].set_state(state['ffpi'        ])
        if 'ffk'          in conf: conf['ffk'         ].set_state(state['ffk'         ])
        if 'collinspi'    in conf: conf['collinspi'   ].set_state(state['collinspi'   ])
        if 'collinsk'     in conf: conf['collinsk'    ].set_state(state['collinsk'    ])
        if 'Htildepi'     in conf: conf['Htildepi'    ].set_state(state['Htildepi'    ])
        if 'Htildek'      in conf: conf['Htildek'     ].set_state(state['Htildek'     ])
  
    def distribute_requests(self,container,requests):
        cnt=0
        for request in requests:
            container[cnt].append(request)
            cnt+=1
            if cnt==self.nworkers: cnt=0

    def get_requests(self):
        container=[[] for _ in range(self.nworkers)]
        if 'sidis'  in conf['datasets']:  self.distribute_requests(container,self.sidisres.requests) 
        if 'sia'    in conf['datasets']:  self.distribute_requests(container,self.siares.requests) 
        if 'AN'     in conf['datasets']:  self.distribute_requests(container,self.ANres.requests) 
        return container

    def task(self,request):
        for i in range(len(request)):
            if  request[i]['reaction']=='sidis' :  self.sidisres.process_request(request[i])
            if  request[i]['reaction']=='sia'   :  self.siares.process_request(request[i])
            if  request[i]['reaction']=='AN'    :  self.ANres.process_request(request[i])
        return request
 
    def get_residuals(self,par):
        self.parman.set_new_params(par)
        state=self.get_state()
        self.parallel.update_workers(state)
        results=self.parallel.send_tasks(self.requests)

        #--update tables with the new theory values
        for chunk in results:
            for request in chunk:
                if request['reaction']=='sidis'  : self.sidisres.update_tabs_external(request)
                if request['reaction']=='sia'    : self.siares.update_tabs_external(request)
                if request['reaction']=='AN'     : self.ANres.update_tabs_external(request)

        #--compute residuals
        res,rres,nres=[],[],[]
        if 'sidis' in conf['datasets']:
            out=self.sidisres.get_residuals(calc=False)
            res=np.append(res,out[0])
            rres=np.append(rres,out[1])
            nres=np.append(nres,out[2])
        if 'sia' in conf['datasets']:
            out=self.siares.get_residuals(calc=False)
            res=np.append(res,out[0])
            rres=np.append(rres,out[1])
            nres=np.append(nres,out[2])
        if 'AN' in conf['datasets']:
            out=self.ANres.get_residuals(calc=False)
            res=np.append(res,out[0])
            rres=np.append(rres,out[1])
            nres=np.append(nres,out[2])
        return res,rres,nres

    def get_data_info(self):

        #--compute residuals
        reaction=[]
        if 'sidis' in conf['datasets']:
            out=self.sidisres.get_residuals(calc=False)
            reaction.extend(['sidis' for _ in out[0]])
        if 'sia' in conf['datasets']:
            out=self.siares.get_residuals(calc=False)
            reaction.extend(['sia' for _ in out[0]])
        if 'AN' in conf['datasets']:
            out=self.ANres.get_residuals(calc=False)
            reaction.extend(['AN' for _ in out[0]])
        return reaction

    def gen_report(self,verb=0,level=0):
        L=[]
        if 'sidis'   in conf['datasets']: L.extend(self.sidisres.gen_report(verb,level))
        if 'sia'     in conf['datasets']: L.extend(self.siares.gen_report(verb,level))
        if 'AN'      in conf['datasets']: L.extend(self.ANres.gen_report(verb,level))
        return L

    def get_chi2(self):
        data={}
        if 'sidis'   in conf['datasets']: data.update(self.sidisres.get_chi2())
        if 'sia'     in conf['datasets']: data.update(self.siares.get_chi2())
        if 'AN'      in conf['datasets']: data.update(self.ANres.get_chi2())
        return data

    def test(self,ntasks=10):
        #--loop over states 
        print '='*20
        t=time.time() 
        for _ in range(ntasks): 
            par=self.parman.par
            par*=(1+0.01*np.random.randn(par.size))
            res,rres,nres=self.get_residuals(par)
            chi2=np.sum(res**2)
            print '(%d/%d) chi2=%f'%(_,ntasks,chi2) 
        print '='*20
        elapsed_time=time.time()-t 
        print 'elapsed time :%f'%elapsed_time
        return elapsed_time

    def shutdown(self):
        self.parallel.stop_workers()

if __name__=='__main__':

    load_config('input.py')
    nworkers=20
    resman=RESMAN(nworkers)
    resman.test()
    resman.shutdown()




