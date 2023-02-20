# -*- coding: utf-8 -*-
"""
    femagtools.opt
    ~~~~~~~~~~~~~~

    Manage multi-objective optimization with FEMAG



"""
import time
import logging
import pathlib
import femagtools
import femagtools.fsl
import femagtools.moproblem
import femagtools.getset
from .moo.algorithm import Nsga2
from .moo.population import Population
from .femag import set_magnet_properties


logger = logging.getLogger(__name__)


def log_pop(pop, ngen):
    objectives = pop.problem.objective_vars
    decisions = pop.problem.decision_vars
    log = [''.join(['Generation: {}\n'.format(ngen),
                    'rank '] +
                   ["{:10s}".format(o['name'].split('.')[-1])
                    for o in objectives] +
                   [" "] +
                   ["{:12s}".format(d['name'].split('.')[-1])
                    for d in decisions])]

    for i in pop.individuals:
        log.append(''.join(["{} ".format(i.rank)] +
                           ["{:10.2f}".format(f) for f in i.cur_f] +
                           ["   "] +
                           ["{:10.4f}".format(x) for x in i.cur_x]))

    log.append(
        '--------------------------------------------------------------------')
    log.append("  znad: {}\n  zi: {}\n  zw: {}\n  Norm Dist: {}".format(
        pop.compute_nadir(),
        pop.compute_ideal(),
        pop.compute_worst(),
        pop.compute_norm_dist()))
    return log


class Optimizer(object):
    # tasktype='Task'):
    def __init__(self, workdir, magnetizingCurves, magnetMat, condMat=[],
                 result_func=None, templatedirs=[]):
        # self.tasktype = tasktype
        self.templatedirs = templatedirs
        self.result_func = result_func
        self.femag = femagtools.Femag(workdir,
                                      magnetizingCurves=magnetizingCurves,
                                      magnets=magnetMat,
                                      condMat=condMat)

    def _update_population(self, generation, pop, engine):
        self.job.cleanup()

        for k, i in enumerate(pop.individuals):
            task = self.job.add_task(self.result_func)
            pop.problem.prepare(i.cur_x, self.model)
            for mc in self.femag.copy_magnetizing_curves(self.model,
                                                         task.directory):
                task.add_file(mc)
            if 'wdgdef' in self.model.windings:
                self.model.windings['wdgfile'] = self.femag.create_wdg_def(
                    self.model)
            set_magnet_properties(self.model, self.fea, self.femag.magnets)
            task.add_file('femag.fsl',
                          self.builder.create(self.model, self.fea,
                                              self.femag.magnets))
            if 'poc' in self.fea:
                task.add_file(self.fea['pocfilename'],
                              self.fea['poc'].content())
            if 'stateofproblem' in self.fea:
                task.set_stateofproblem(fea['stateofproblem'])
        tstart = time.time()
        ntasks = engine.submit()
        status = engine.join()
        tend = time.time()

        for t, i in zip(self.job.tasks, pop.individuals):
            if t.status == 'C':
                r = t.get_results()
                if isinstance(r, dict) and 'error' in r:
                    logger.warn("Task %s failed: %s", t.id, r['error'])
                else:
                    if isinstance(r, dict):
                        pop.problem.setResult(
                            femagtools.getset.GetterSetter(r))
                    else:
                        pop.problem.setResult(r)

                    i.cur_f = pop.problem.objfun([])
                    i.results = {k: v for k, v in r.items()}
            else:
                logger.warn("Task %s failed with status %s", t.id, t.status)
                i.cur_f = [float('nan')]*pop.problem.f_dim

            i.generation = generation  # for reporting purposes

        pop.update()
        return tend - tstart

    def __call__(self, num_generations, opt, pmMachine,
                 operatingConditions, engine):
        return self.optimize(num_generations, opt, pmMachine,
                             operatingConditions, engine)

    def optimize(self, num_generations, opt, pmMachine,
                 operatingConditions, engine):
        """execute optimization"""
        decision_vars = opt['decision_vars']
        objective_vars = opt['objective_vars']
        population_size = opt['population_size']

        problem = femagtools.moproblem.FemagMoProblem(decision_vars,
                                                      objective_vars)
        self.builder = femagtools.fsl.Builder(self.templatedirs)
        self.model = femagtools.model.MachineModel(pmMachine)
        self.fea = operatingConditions
        self.fea.update(self.model.windings)
        self.fea['lfe'] = self.model.lfe
        self.fea['move_action'] = self.model.move_action
        self.fea['phi_start'] = 0.0
        self.fea['range_phi'] = 720/self.model.get('poles')
        self.pop = Population(problem, population_size)

        algo = Nsga2()

        self.job = engine.create_job(self.femag.workdir)
        # for progress logger
        self.job.num_cur_steps = femagtools.model.FeaModel(
            self.fea).get_num_cur_steps()

        logger.info("Optimize x:%d f:%d generations:%d population size:%d",
                    len(self.pop.problem.decision_vars),
                    len(self.pop.problem.objective_vars),
                    num_generations,
                    self.pop.size())

        results = dict(rank=[], f=[], x=[])
        elapsedTime = 0
        for i in range(num_generations):
            logger.info("Generation %d", i)
            if i > 0:
                newpop = algo.evolve(self.pop)
                deltat = self._update_population(i, newpop, engine)
                self.pop.merge(newpop)
            else:
                deltat = self._update_population(i, self.pop, engine)
            pop_report = '\n'.join(log_pop(self.pop, i) +
                                   ['', '  Elapsed Time: {} s'.format(
                                       int(deltat))])
            repfile = pathlib.Path(
                self.femag.workdir) / f'population-{i}.dat'
            repfile.write_text(pop_report)
            logger.info(pop_report)
            elapsedTime += deltat
        logger.info("TOTAL Elapsed Time: %d s", elapsedTime)
        ft = []
        xt = []
        for i in self.pop.individuals:
            results['rank'].append(i.rank)
            ft.append(i.cur_f)
            xt.append(i.cur_x)
        objective_vars = self.pop.problem.objective_vars
        decision_vars = self.pop.problem.decision_vars
        results['f'] = [[s.get('sign', 1)*y for y in f]
                        for s, f in zip(objective_vars, zip(*ft))]
        results['x'] = list(zip(*xt))
        results['znad'] = [s.get('sign', 1)*v
                           for s, v in zip(objective_vars,
                                           self.pop.compute_nadir())]
        results['zi'] = [s.get('sign', 1)*v
                         for s, v in zip(objective_vars,
                                         self.pop.compute_ideal())]
        results['zw'] = [s.get('sign', 1)*v
                         for s, v in zip(objective_vars,
                                         self.pop.compute_worst())]
        results['dist'] = self.pop.compute_norm_dist()

        def label(d):
            for n in ('desc', 'label', 'name'):
                if n in d:
                    return d
            return '<?>'
        results['objective'] = [label(o) for o in objective_vars]
        results['decision'] = [label(d) for d in decision_vars]
        results['population'] = [i.results
                                 for i in self.pop.individuals if hasattr(i, 'results')]
        return results

    # print("\nChampion: {}\n".format(pop.champion['f']))
        # if flast != None:
        #    print("Fitness Comparison:")
        #    for f1, f2 in zip(pop.champion['f'], flast):
        #        print( "{:10.2f} {:10.2f}      {:10.2f}".format(f1, f2, f1-f2))
        # flast = list(pop.champion['f'])
        # print("")
#    except:
#        print "Unexpected error:", sys.exc_info()

#    print("L2 distance to the best decision vector:")
#    for best_decision in prob.best_x:
#        l2_norm = 0
#        for n in range(0, len(best_decision)):
#            l2_norm +=  (best_decision[n] - isl.population.champion.x[n]) ** 2
#        l2_norm = sqrt(l2_norm)
#        print(l2_norm)

# pf=pop.plot_pareto_fronts()
# savefig('pf0.png')
