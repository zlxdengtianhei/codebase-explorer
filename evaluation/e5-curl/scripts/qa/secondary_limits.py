"""Count tokens per request; stop between admitted S/C pairs; frozen prompts unchanged."""
import json,threading,time
class SecondaryBudgetReached(Exception):pass
class Limits:
 def __init__(self,E,main_judge_tokens):
  self.E=E;self.lock=threading.RLock();self.data={'main_judge_tokens':main_judge_tokens,'main_answers':120,'main_judge_tokens_per_answer':main_judge_tokens/120,'planned_secondary_answers':40,'judge_limit':1.5*40*main_judge_tokens/120,'answer_input_limit':15000000,'answer_input':0,'answer_output':0,'judge_tokens':0,'answer_stopped':False,'judge_stopped':False,'answer_requests':0,'judge_requests':0,'answer_unknown_usage_failures':0,'judge_unknown_usage_failures':0,'answer_inflight':0,'judge_inflight':0,'answer_active_pair':None,'judge_active_pair':None,'completed_answer_pairs':[],'completed_judge_pairs':[],'stop_unit':'Finish an admitted S/C question pair; admit no subsequent pair after the corresponding cap is reached','formula':'judge_limit = 1.5 * 40 * (main observed five + rubric input-including-cache + output) / 120'};self.persist()
 def persist(self):
  self.data['updated_epoch']=time.time();p=self.E/'secondary-limits.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(self.data,indent=2));tmp.replace(p)
 def begin_pair(self,kind,qid):
  with self.lock:
   if self.data[kind+'_stopped']:return False
   assert self.data[kind+'_active_pair'] is None
   self.data[kind+'_active_pair']=qid;self.persist();return True
 def end_pair(self,kind,qid):
  with self.lock:
   assert self.data[kind+'_active_pair']==qid
   self.data[kind+'_active_pair']=None;self.data['completed_'+kind+'_pairs'].append(qid);self.persist()
 def before(self,kind):
  with self.lock:
   if self.data[kind+'_stopped'] and self.data[kind+'_active_pair'] is None:raise SecondaryBudgetReached(kind+' limit reached; no subsequent pair admitted')
   self.data[kind+'_requests']+=1;self.data[kind+'_inflight']+=1;self.persist()
 def after(self,kind,usage=None):
  with self.lock:
   self.data[kind+'_inflight']-=1
   if usage:
    if not isinstance(usage,dict):usage=usage.model_dump()
    prompt=usage.get('prompt_tokens',0);output=usage.get('completion_tokens',0)
    if kind=='answer':
     self.data['answer_input']+=prompt;self.data['answer_output']+=output;self.data['answer_stopped']=self.data['answer_input']>=self.data['answer_input_limit']
    else:self.data['judge_tokens']+=prompt+output;self.data['judge_stopped']=self.data['judge_tokens']>=self.data['judge_limit']
   else:self.data[kind+'_unknown_usage_failures']+=1
   self.persist()
 def snapshot(self):
  with self.lock:return dict(self.data)
 def install(self,rt):
  real=rt.real_completion;original_five=rt.judge.TrackingClient.create;original_rubric=rt.rubric.request
  def answer(*a,**kw):
   self.before('answer')
   try:result=real(*a,**kw)
   except BaseException:self.after('answer');raise
   self.after('answer',getattr(result,'usage',None));return result
  def five(tc,**kw):
   self.before('judge')
   try:result=original_five(tc,**kw)
   except BaseException:self.after('judge');raise
   self.after('judge',getattr(result,'usage',None));return result
  def rubric(*a,**kw):
   self.before('judge')
   try:result=original_rubric(*a,**kw)
   except BaseException:self.after('judge');raise
   self.after('judge',result['response'].get('usage'));return result
  rt.real_completion=answer;rt.judge.TrackingClient.create=five;rt.rubric.request=rubric
