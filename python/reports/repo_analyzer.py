import json;

# Showcases how a report file may be analyzed for specific data

repos = ["tomcat", "hudi", "django", "strider", "pydriller"]

for r in repos:
    fl = open("report_" + r + ".json", "r")
    repo = json.loads(fl.read())
    
    avg_contrib = 0    
    # Average top 10 devs contribution in packages
    for package in repo['children']:
        package['contributors'].sort(key = (lambda x: x['contrib']['LOC+']), reverse=True)

        all = 1 + sum(list(map(lambda c: c['contrib']['LOC+'], package['contributors'])))
        contrib = 0.0
        for i in range(0, min(len(package['contributors']), 10)):
            contrib += float(package['contributors'][i]['contrib']['LOC+']) / float(all)

        print(r + ' ' + str(contrib) + ' in package ' + package['name'])
        
